import util
import time
import ipaddress
import socket

# O programa deve enviar TTLs no intervalo [1, TRACEROUTE_MAX_TTL], inclusive.
# Tecnicamente, o IPv4 permite TTLs de ate 255, mas, na pratica, isso e excessivo.
# A maioria das implementacoes de traceroute limita o valor a aproximadamente 30.
TRACEROUTE_MAX_TTL = 30

# A Cisco popularizou o uso das portas UDP no intervalo [33434, 33464] para traceroute.
# Embora isso nao seja um padrao formal, alguns roteadores na Internet respondem de forma
# mais consistente com mensagens ICMP de tempo excedido para pacotes UDP enviados a essas
# portas. Voce pode usar outra porta, mas este valor e adequado para o projeto.
TRACEROUTE_PORT_NUMBER = 33434

# Pacotes podem ser descartados na Internet. PROBE_ATTEMPT_COUNT e o numero maximo de
# sondas que a funcao traceroute deve enviar para um mesmo TTL antes de seguir adiante.
PROBE_ATTEMPT_COUNT = 3


FAIXAS_CLASSIFICACAO = [
    (ipaddress.ip_network("127.0.0.0/8"), "LOOPBACK"),
    (ipaddress.ip_network("169.254.0.0/16"), "LINK-LOCAL"),
    (ipaddress.ip_network("224.0.0.0/4"), "MULTICAST"),
    (ipaddress.ip_network("10.0.0.0/8"), "REDE PRIVADA"),
    (ipaddress.ip_network("172.16.0.0/12"), "REDE PRIVADA"),
    (ipaddress.ip_network("192.168.0.0/16"), "REDE PRIVADA"),
    (ipaddress.ip_network("100.64.0.0/10"), "CGNAT"),
    (ipaddress.ip_network("192.0.2.0/24"), "DOCUMENTACAO"),
    (ipaddress.ip_network("198.51.100.0/24"), "DOCUMENTACAO"),
    (ipaddress.ip_network("203.0.113.0/24"), "DOCUMENTACAO"),
    (ipaddress.ip_network("0.0.0.0/8"), "RESERVADA"),
    (ipaddress.ip_network("240.0.0.0/4"), "RESERVADA"),
]


def classificar_rede(ip:str) -> str:
    addr = ipaddress.ip_address(ip)

    for rede, rotulo in FAIXAS_CLASSIFICACAO:
        if addr in rede:
            return rotulo

    return "PUBLICA"


def print_result_melhorado(roteadores: list[str], ttl: int, tempos: dict[str, list[float]]) -> None:
    if len(roteadores) == 0:
        print(f"{ttl: >2}: * * *")
        return

    for i, roteador in enumerate(roteadores):
        if i == 0:
            preamble = f"{ttl: >2}"
        else:
            preamble = "   "

        try:
            hostname, _, _ = socket.gethostbyaddr(roteador)
            nome = f"{hostname} ({roteador})"
        except socket.herror:
            nome = roteador

        tempos_formatados = ""
        for t in tempos.get(roteador, []):
            tempos_formatados += f"{t:.3f} ms   "

        rotulo = classificar_rede(roteador)
        print(f"{preamble}  {nome}  {tempos_formatados}[{rotulo}]")


class IPv4:
    # Cada membro abaixo corresponde a um campo do cabecalho IPv4. Os campos aparecem
    # na mesma ordem em que estao no pacote. Todos devem ser armazenados na ordem de
    # bytes do host.
  
    version: int
    header_len: int  # Comprimento em bytes, e nao o valor bruto armazenado no pacote.
    tos: int         # Tambem chamado de bits DSCP e ECN.
    length: int      # Comprimento total do pacote.
    id: int
    flags: int
    frag_offset: int
    ttl: int
    proto: int
    cksum: int
    src: str
    dst: str

    def __init__(self, buffer: bytes):
        vihl = buffer[0]
        self.version = vihl >> 4
        self.header_len = calcular_inicio_cabecalho_transporte(buffer)
        self.tos = buffer[1]
        self.length = int.from_bytes(buffer[2:4], "big")
        self.id = int.from_bytes(buffer[4:6], "big")
        flags_e_offset = int.from_bytes(buffer[6:8], "big")
        self.flags = flags_e_offset >> 13
        self.frag_offset = flags_e_offset & 0x1FFF
        self.ttl = buffer[8]
        self.proto = buffer[9]
        self.cksum = int.from_bytes(buffer[10:12], "big")
        self.src = util.inet_ntoa(buffer[12:16])
        self.dst = util.inet_ntoa(buffer[16:20])

    def __str__(self) -> str:
        return f"IPv{self.version} (tos 0x{self.tos:x}, ttl {self.ttl}, " + \
            f"id {self.id}, flags 0x{self.flags:x}, " + \
            f"offset {self.frag_offset}, " + \
            f"proto {self.proto}, header_len {self.header_len}, " + \
            f"len {self.length}, cksum 0x{self.cksum:x}) " + \
            f"{self.src} > {self.dst}"


class ICMP:
    # Cada membro abaixo corresponde a um campo do cabecalho ICMP. Os campos aparecem
    # na mesma ordem em que estao no pacote. Todos devem ser armazenados na ordem de
    # bytes do host.
   
    type: int
    code: int
    cksum: int

    def __init__(self, buffer: bytes):
        self.type = buffer[0]
        self.code = buffer[1]
        self.cksum = int.from_bytes(buffer[2:4], "big")

    def __str__(self) -> str:
        return f"ICMP (type {self.type}, code {self.code}, " + \
            f"cksum 0x{self.cksum:x})"


class UDP:
    # Cada membro abaixo corresponde a um campo do cabecalho UDP. Os campos aparecem
    # na mesma ordem em que estao no pacote. Todos devem ser armazenados na ordem de
    # bytes do host.
 
    src_port: int
    dst_port: int
    len: int
    cksum: int

    def __init__(self, buffer: bytes):
        self.src_port = int.from_bytes(buffer[0:2], "big")
        self.dst_port = int.from_bytes(buffer[2:4], "big")
        self.len = int.from_bytes(buffer[4:6], "big")
        self.cksum = int.from_bytes(buffer[6:8], "big")

    def __str__(self) -> str:
        return f"UDP (src_port {self.src_port}, dst_port {self.dst_port}, " + \
            f"len {self.len}, cksum 0x{self.cksum:x})"


def calcular_inicio_cabecalho_transporte(buffer: bytes) -> int:
    return (buffer[0] & 0x0F) * 4


def classificar_resposta_icmp(icmp: ICMP) -> str:
    if icmp.type == 11 and icmp.code == 0:
        return "tempo_excedido"
    if icmp.type == 3 and icmp.code == 3:
        return "porta_inalcancavel"
    return "ignorar"


def deve_encerrar_traceroute(ip_origem: str, ip_destino: str, icmp: ICMP) -> bool:
    return ip_origem == ip_destino and \
        classificar_resposta_icmp(icmp) == "porta_inalcancavel"


def registrar_roteador_descoberto(roteadores_ttl: list[str], endereco: str) -> bool:
    if endereco in roteadores_ttl:
        return False
    roteadores_ttl.append(endereco)
    return True


def interpretar_resposta_da_sonda(buffer: bytes):
    if len(buffer) < 20:
        return None
    ip_externo = IPv4(buffer)
    inicio_icmp = calcular_inicio_cabecalho_transporte(buffer)
    if ip_externo.proto != util.IPPROTO_ICMP or \
            len(buffer) < inicio_icmp + 8:
        return None
    icmp = ICMP(buffer[inicio_icmp:inicio_icmp + 8])

    inicio_ip_interno = inicio_icmp + 8
    if len(buffer) < inicio_ip_interno + 20:
        return ip_externo, icmp, None, None
    pacote_interno = buffer[inicio_ip_interno:]
    ip_interno = IPv4(pacote_interno)
    inicio_udp = calcular_inicio_cabecalho_transporte(pacote_interno)
    if ip_interno.proto != util.IPPROTO_UDP or \
            len(pacote_interno) < inicio_udp + 8:
        return ip_externo, icmp, ip_interno, None
    udp = UDP(pacote_interno[inicio_udp:inicio_udp + 8])
    return ip_externo, icmp, ip_interno, udp


def resposta_pertence_a_sonda(ip_interno, udp, ip_destino: str) -> bool:
    if ip_interno is None or udp is None:
        return False
    return ip_interno.dst == ip_destino and \
        udp.dst_port == TRACEROUTE_PORT_NUMBER

def traceroute(sendsock: util.Socket, recvsock: util.Socket, ip: str) -> list[list[str]]:
    """Descobre o caminho ate `ip` imprimindo cada salto com tempo (ms) e classe de rede.

    Envia 3 sondas UDP por TTL, recebe as respostas ICMP e monta uma lista
    de listas: cada nivel interno guarda os IPs descobertos naquele TTL.
    """

    caminho = []
    for ttl in range(1, TRACEROUTE_MAX_TTL + 1):
        roteadores_ttl = []
        tempos_ttl: dict[str, list[float]] = {}       #
        destino_alcancado = False

        for _ in range(PROBE_ATTEMPT_COUNT):
            sendsock.set_ttl(ttl)
            t_envio = time.monotonic()                
            sendsock.sendto("Potato".encode(), (ip, TRACEROUTE_PORT_NUMBER))

            while recvsock.recv_select():
                buf, _endereco = recvsock.recvfrom()
                interpretado = interpretar_resposta_da_sonda(buf)
                if interpretado is None:
                    continue
                ip_externo, icmp, ip_interno, udp = interpretado
                if not resposta_pertence_a_sonda(ip_interno, udp, ip):
                    continue

                classe = classificar_resposta_icmp(icmp)
                if classe == "ignorar":
                    continue

                rtt_ms = (time.monotonic() - t_envio) * 1000      
                if ip_externo.src not in tempos_ttl:              
                    tempos_ttl[ip_externo.src] = []               
                tempos_ttl[ip_externo.src].append(rtt_ms)         

                if deve_encerrar_traceroute(ip_externo.src, ip, icmp):
                    destino_alcancado = True
                else:
                    registrar_roteador_descoberto(roteadores_ttl, ip_externo.src)
                break

            if destino_alcancado:
                break

        if destino_alcancado:
            roteadores_ttl = []
            registrar_roteador_descoberto(roteadores_ttl, ip)

        print_result_melhorado(roteadores_ttl, ttl, tempos_ttl)
        

        caminho.append(roteadores_ttl)

        if destino_alcancado:
            break

    return caminho

if __name__ == '__main__':
    args = util.parse_args()
    ip_addr = util.gethostbyname(args.host)
    print(f"traceroute to {args.host} ({ip_addr})")
    traceroute(util.Socket.make_udp(), util.Socket.make_icmp(), ip_addr)
