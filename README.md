# Traceroute

Implementação do comando `traceroute` escrita do zero em **Python puro**, usando apenas a
biblioteca padrão. Os cabeçalhos **IPv4**, **ICMP** e **UDP** são interpretados manualmente,
byte a byte, a partir dos pacotes recebidos — nenhum comando do sistema (`traceroute`,
`ping`) é executado por baixo dos panos.

Projeto desenvolvido na disciplina de **Redes de Computadores**.

---

## Sumário

- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Como executar](#como-executar)
  - [Linux](#linux)
  - [macOS](#macos)
  - [Windows](#windows)
- [Exemplos de destinos para teste](#exemplos-de-destinos-para-teste)
- [Entendendo a saída](#entendendo-a-saída)
- [Classificação dos endereços](#classificação-dos-endereços)
- [Configurações do programa](#configurações-do-programa)
- [Solução de problemas](#solução-de-problemas)
- [Estrutura do projeto](#estrutura-do-projeto)

---

## Requisitos

| Item | Detalhe |
| --- | --- |
| Python | 3.9 ou superior (o código usa anotações `list[str]`). Testado com 3.14. |
| Dependências | **Nenhuma**. Somente a biblioteca padrão — `pip install` não é necessário. |
| Privilégios | Criar *raw socket* ICMP. Exige **root/administrador** no Linux e no Windows. |

> **Por que precisa de privilégio?**
> O programa abre um socket `SOCK_RAW` com `IPPROTO_ICMP` para *receber* as mensagens
> ICMP "time exceeded" (tipo 11) devolvidas por cada roteador intermediário. Criar
> sockets raw é uma operação restrita ao superusuário no Linux e a administradores no
> Windows. No macOS existe um caminho alternativo sem privilégios (veja abaixo).

Verifique a versão do Python instalada:

```bash
python3 --version    # Linux / macOS
python --version     # Windows
```

---

## Instalação

```bash
git clone https://github.com/doriedsonmoreira/Traceroute.git
cd Traceroute
```

Não há dependências para instalar. Você já pode executar o programa.

---

## Como executar

O programa recebe **um único argumento**: o host (nome de domínio ou endereço IPv4) de
destino.

```bash
python3 traceroute.py <destino>
```

Exemplo rápido:

```bash
python3 traceroute.py 8.8.8.8
```

### Linux

```bash
git clone https://github.com/doriedsonmoreira/Traceroute.git
cd Traceroute

python3 traceroute.py google.com
```

Se a saída for:

```
PermissionError: execute o programa como administrador/root.
```

o socket raw não pôde ser criado. Rode com `sudo`:

```bash
sudo python3 traceroute.py google.com
```

**Alternativa sem `sudo`** — concede a capacidade `cap_net_raw` ao interpretador:

```bash
sudo setcap cap_net_raw+ep "$(readlink -f "$(which python3)")"
python3 traceroute.py google.com      # agora funciona sem sudo
```

> ⚠️ Cuidado: o `setcap` vale para **todo** script rodado com aquele `python3`.
> Se preferir, apague a capacidade depois de usar:
> `sudo setcap -r "$(readlink -f "$(which python3)")"`.

### macOS

```bash
git clone https://github.com/doriedsonmoreira/Traceroute.git
cd Traceroute

python3 traceroute.py google.com
```

No macOS, quando a criação do socket raw falha por falta de privilégio, o próprio programa
troca automaticamente para um socket ICMP do tipo *datagram* (sem privilégios) — o mesmo
mecanismo usado pelo `traceroute` nativo do sistema.

Para capturar as respostas de **todos** os saltos (e evitar `* * *` em alguns pontos),
prefira executar como root:

```bash
sudo python3 traceroute.py google.com
```

Se o macOS exibir o aviso *"Would you like the application Python to accept incoming
network connections?"*, permita — caso contrário o ICMP de retorno é bloqueado.

### Windows

1. Instale o **Python 3.9+** ([python.org](https://www.python.org/downloads/windows/) ou
   Microsoft Store). Marque a opção **"Add Python to PATH"** durante a instalação.
2. Abra o **PowerShell (ou Terminal) como Administrador** — clique com o botão direito em
   "Terminal" → **Executar como administrador**. No Windows, *raw sockets* exigem
   privilégio administrativo.
3. Execute:

```powershell
git clone https://github.com/doriedsonmoreira/Traceroute.git
cd Traceroute

python traceroute.py google.com
```

> Se o `python` não for reconhecido, use o *launcher* do Windows: `py traceroute.py google.com`.
>
> Não existe `sudo` no Windows — a elevação é feita pelo terminal aberto como administrador.
> Se a janela **não** estiver elevada, o programa imprime
> `PermissionError: execute o programa como administrador/root.` e encerra.

---

## Exemplos de destinos para teste

### Endereços IPv4

| Destino | Descrição | O que demonstra |
| --- | --- | --- |
| `127.0.0.1` | Loopback | 1 salto, resposta imediata, tag `[LOOPBACK]` |
| `192.168.0.1` | Rede privada | 1º salto (se for o seu roteador), tag `[REDE PRIVADA]` |
| `10.0.0.1` / `172.16.0.1` | Redes privadas RFC 1918 | Classificação `[REDE PRIVADA]` |
| `8.8.8.8` | Google Public DNS | Caminho completo até a Internet |
| `1.1.1.1` | Cloudflare DNS | Caminho até a Internet por outra rota |
| `9.9.9.9` | Quad9 DNS | Terceiro caminho para comparar rotas |
| `169.254.169.254` | Link-local (AWS/GCP/Azure) | Tag `[LINK-LOCAL]` |
| `100.64.0.1` | Faixa CGNAT (RFC 6598) | Tag `[CGNAT]` |
| `192.0.2.1` / `198.51.100.1` / `203.0.113.1` | TEST-NET (documentação) | Tag `[DOCUMENTACAO]` — **não são roteáveis**, espere `* * *` |
| `224.0.0.1` | Multicast | Tag `[MULTICAST]` |
| `0.0.0.0` | Reservado | Tag `[RESERVADA]` |

> **Melhores alvos para o teste real:** `8.8.8.8`, `1.1.1.1` e `9.9.9.9` respondem ICMP de
> forma confiável e não filtram o "port unreachable" que encerra o traceroute.

### Nomes de domínio (DNS)

O programa resolve o nome para IPv4 automaticamente (`gethostbyname`).

| Destino | Descrição |
| --- | --- |
| `google.com` | Página inicial do Google |
| `github.com` | GitHub |
| `cloudflare.com` | Cloudflare |
| `dns.google` | Resolver do Google (resolve para `8.8.8.8`) |
| `one.one.one.one` | Resolver da Cloudflare (resolve para `1.1.1.1`) |
| `registro.br` | Registro.br — rota dentro do Brasil |
| `uol.com.br` | UOL — rota dentro do Brasil |
| `www.youtube.com` | CDN com vários IPs, bom para ver caminhos diferentes |

### Bateria de teste rápida

```bash
for destino in 127.0.0.1 8.8.8.8 1.1.1.1 google.com registro.br; do
    echo "=== traceroute para $destino ==="
    sudo python3 traceroute.py "$destino"
    echo
done
```

---

## Entendendo a saída

```
traceroute to 8.8.8.8 (8.8.8.8)
 1  _gateway (192.168.0.1)  1.234 ms   1.456 ms   1.789 ms   [REDE PRIVADA]
 2  10.0.0.1  5.000 ms   5.100 ms   5.200 ms   [REDE PRIVADA]
 3: * * *
 4  dns.google (8.8.8.8)  12.345 ms   12.400 ms   12.380 ms   [PUBLICA]
```

| Trecho | Significado |
| --- | --- |
| `1`, `2`, `4` | Número do salto (valor do TTL enviado) |
| `_gateway (192.168.0.1)` | Endereço do roteador e nome DNS (quando existe PTR) |
| `1.234 ms` | Tempo de ida e volta (RTT) de cada uma das 3 sondas |
| `* * *` | Nenhuma resposta neste TTL (roteador descartou ou o ICMP foi bloqueado) |
| `[REDE PRIVADA]` | Classificação do endereço do salto |

Formato exato: `f"{ttl: >2}  {nome}  {tempos}[{classe}]"` — as 3 sondas de um mesmo TTL
podem vir de roteadores **diferentes** (roteamento ECMP); nesse caso, cada endereço
aparece em uma linha própria, com o TTL impresso apenas na primeira.

---

## Classificação dos endereços

Cada IP de salto é classificado automaticamente:

| Faixa | Tag |
| --- | --- |
| `127.0.0.0/8` | `LOOPBACK` |
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | `REDE PRIVADA` |
| `100.64.0.0/10` | `CGNAT` |
| `169.254.0.0/16` | `LINK-LOCAL` |
| `224.0.0.0/4` | `MULTICAST` |
| `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` | `DOCUMENTACAO` |
| `0.0.0.0/8`, `240.0.0.0/4` | `RESERVADA` |
| qualquer outro | `PUBLICA` |

---

## Configurações do programa

As constantes ficam no topo de `traceroute.py` e `util.py`:

| Constante | Padrão | Onde | Significado |
| --- | --- | --- | --- |
| `TRACEROUTE_MAX_TTL` | `30` | `traceroute.py` | TTL máximo (número máximo de saltos) |
| `TRACEROUTE_PORT_NUMBER` | `33434` | `traceroute.py` | Porta UDP usada nas sondas (faixa clássica da Cisco) |
| `PROBE_ATTEMPT_COUNT` | `3` | `traceroute.py` | Sondas enviadas por TTL |
| `SELECT_TIMEOUT` | `2` | `util.py` | Segundos de espera por resposta antes de desistir do salto |

Para alterar, basta editar o valor e executar novamente.

---

## Solução de problemas

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `PermissionError: execute o programa como administrador/root.` | Sem privilégio para abrir *raw socket* | Linux/macOS: use `sudo`. Windows: abra o terminal como Administrador. |
| `socket.gaierror` | O nome de domínio não resolveu | Verifique a digitação e a sua conexão com a Internet. |
| `* * *` em **todos** os saltos | ICMP/UDP filtrado pelo firewall ou pela rede | Tente `sudo`, teste com `8.8.8.8` e desative temporariamente o firewall. |
| Só o **primeiro** salto responde | O destino não devolve "port unreachable" | O TTL foi esgotado (30 saltos) ou o ICMP de erro está bloqueado. |
| Um salto responde, mas com **latência alta** | O TTL não está sendo varied | Normal em VPNs/NAT — o TTL inicial do SO também conta. |
| `MacOS` + `* * *` nos saltos do meio | ICMP bloqueado pelo firewall do macOS | Libere o Python em *Ajustes do Sistema → Firewall* ou rode com `sudo`. |
| Funciona no Linux mas não no Windows | Terminal não elevado | Execute o PowerShell como Administrador. |

Comparação rápida com o traceroute do sistema (útil para validar os resultados):

```bash
traceroute 8.8.8.8          # Linux/macOS
tracert 8.8.8.8             # Windows
```

---

## Estrutura do projeto

```
Traceroute/
├── traceroute.py   # lógica principal: classes IPv4/ICMP/UDP, sondas, classificação e impressão
├── util.py         # utilitários: wrapper de sockets, seleção de SO, timeout e argumentos
├── .gitignore
└── README.md
```

- **`traceroute.py`** — define as classes `IPv4`, `ICMP` e `UDP` (que fazem o *parsing* dos
  cabeçalhos), a classificação de faixas (`FAIXAS_CLASSIFICACAO`) e o laço principal
  `traceroute()`.
- **`util.py`** — encapsula `socket`/`select` atrás da classe `Socket`, resolve o host e
  trata a diferença entre Linux, macOS e Windows na criação do socket ICMP.
