# Traceroute

Implementação do comando `traceroute` escrita do zero em **Python puro** — sem dependências
e sem chamar `traceroute`/`ping` do sistema. Os cabeçalhos **IPv4**, **ICMP** e **UDP** são
interpretados manualmente, byte a byte, a partir dos pacotes recebidos.

Projeto desenvolvido na disciplina de **Redes de Computadores**.

**Exemplo de saída:**

```
traceroute to 8.8.8.8 (8.8.8.8)
 1  _gateway (192.168.0.1)  1.234 ms   1.456 ms   1.789 ms   [REDE PRIVADA]
 2  10.0.0.1  5.000 ms   5.100 ms   5.200 ms   [REDE PRIVADA]
 3: * * *
 4  dns.google (8.8.8.8)  12.345 ms   12.400 ms   12.380 ms   [PUBLICA]
```

O número é o salto (TTL), o endereço vem entre parênteses com o nome DNS quando existe PTR,
os tempos são os RTTs das 3 sondas e a tag entre colchetes classifica a faixa do IP.

## O que o programa faz

- Envia 3 sondas UDP para a porta `33434` com TTL de 1 a 30.
- Cada roteador intermediário responde com ICMP *time exceeded* (tipo 11) — a origem da
  resposta é o próprio roteador.
- Encerra quando o destino responde *port unreachable* (tipo 3, código 3).
- Mede o RTT de cada sonda e classifica o IP do salto (pública, privada, CGNAT, loopback...).

## Requisitos

- **Python 3.9+** (usa anotações `list[str]`); testado com 3.14.
- **Nenhuma dependência** — só a biblioteca padrão, sem `pip install`.
- **Privilégio para abrir raw socket ICMP**: root no Linux/macOS, Administrador no Windows.

> O socket `SOCK_RAW`/`IPPROTO_ICMP` é usado para *receber* as mensagens "time exceeded" de
> cada salto. Criar raw socket é restrito ao superusuário no Linux e a administradores no
> Windows. No macOS existe um caminho alternativo sem privilégios (veja abaixo).

## Como executar

```bash
git clone https://github.com/doriedsonmoreira/Traceroute.git
cd Traceroute

python3 traceroute.py <destino>
```

### Linux

```bash
sudo python3 traceroute.py google.com
```

Sem `sudo`? Conceda a capacidade de raw socket ao interpretador:

```bash
sudo setcap cap_net_raw+ep "$(readlink -f "$(which python3)")"
python3 traceroute.py google.com
```

> ⚠️ O `setcap` vale para **todo** script rodado com aquele `python3`. Para reverter:
> `sudo setcap -r "$(readlink -f "$(which python3)")"`.

### macOS

```bash
python3 traceroute.py google.com
```

Quando a criação do raw socket falha por falta de privilégio, o próprio código troca
automaticamente para um socket ICMP *datagram* (sem privilégios) — o mesmo mecanismo do
`traceroute` nativo do macOS. Para capturar todos os saltos, prefira:

```bash
sudo python3 traceroute.py google.com
```

Se o macOS perguntar se o Python pode aceitar conexões de rede, **permita** — senão o ICMP
de retorno é bloqueado.

### Windows

Raw socket exige privilégio administrativo, então abra o **PowerShell como Administrador**
(botão direito → *Executar como administrador*). No Windows não existe `sudo`.

```powershell
python traceroute.py google.com
```

Use `py` no lugar de `python` se o launcher do Windows estiver instalado. Sem terminal
elevado, o programa avisa `PermissionError: execute o programa como administrador/root.`
e encerra.

## Destinos para teste

| Destino | O que demonstra |
| --- | --- |
| `127.0.0.1` | 1 salto, resposta imediata, tag `[LOOPBACK]` |
| `192.168.0.1` | 1º salto (se for seu roteador), tag `[REDE PRIVADA]` |
| `8.8.8.8` | Google Public DNS — caminho completo até a Internet |
| `1.1.1.1` / `9.9.9.9` | Cloudflare / Quad9 — rotas alternativas para comparar |
| `169.254.169.254` | Link-local (AWS, GCP, Azure) — tag `[LINK-LOCAL]` |
| `100.64.0.1` | Faixa CGNAT (RFC 6598) — tag `[CGNAT]` |
| `192.0.2.1` | TEST-NET-1 (documentação) — tag `[DOCUMENTACAO]`, mas **não é roteável**: espere `* * *` |
| `google.com` | Resolução de nome DNS → IPv4 |
| `github.com` | Caminho até um CDN anycast |
| `dns.google` / `one.one.one.one` | Resolvers que respondem ICMP sem filtro |
| `registro.br` / `uol.com.br` | Rota dentro do Brasil |

Melhores alvos para o teste real: `8.8.8.8`, `1.1.1.1` e `9.9.9.9` — respondem ICMP de
forma confiável e não filtram o "port unreachable" que encerra o traceroute.

Bateria rápida:

```bash
for d in 127.0.0.1 8.8.8.8 1.1.1.1 google.com registro.br; do
    echo "=== $d ==="; sudo python3 traceroute.py "$d"; echo
done
```

## Como funciona

1. `gethostbyname` resolve o nome para IPv4.
2. Um socket UDP envia a sonda; um socket ICMP raw recebe as respostas.
3. Para cada TTL (1 a 30) o TTL da sonda é ajustado e **3 sondas** são enviadas.
4. A resposta ICMP é validada (tipo 11 = salto, tipo 3/código 3 = destino) e o pacote UDP
   embutido é conferido para garantir que a resposta pertence à sonda atual.
5. O RTT de cada sonda é medido com `time.monotonic()` e impresso junto do IP do salto.
6. O programa para ao alcançar o destino ou ao esgotar os 30 TTLs.

## Problemas comuns

- **`PermissionError: execute o programa como administrador/root.`** → falta privilégio:
  use `sudo` (Linux/macOS) ou terminal como Administrador (Windows).
- **`socket.gaierror`** → o nome não resolveu; confira a digitação e a conexão.
- **`* * *` em todos os saltos** → ICMP/UDP filtrado por firewall ou pela rede; teste com
  `8.8.8.8` e desative o firewall temporariamente.
- **Só o primeiro salto responde** → o destino não devolveu "port unreachable" (TTL
  esgotado em 30 ou ICMP de erro bloqueado).
- **No macOS, saltos do meio sem resposta** → libere o Python em *Ajustes do Sistema →
  Firewall* ou rode com `sudo`.

Para validar os resultados, compare com o traceroute do sistema: `traceroute 8.8.8.8` no
Linux/macOS e `tracert 8.8.8.8` no Windows.

## Estrutura do projeto

- **`traceroute.py`** — classes `IPv4`, `ICMP` e `UDP` (parsing dos cabeçalhos),
  classificação de faixas e o laço principal `traceroute()`.
- **`util.py`** — wrapper de `socket`/`select` na classe `Socket`, resolução do host e o
  tratamento das diferenças entre Linux, macOS e Windows na criação do socket ICMP.
