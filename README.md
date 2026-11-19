# MQTT × MQTT-SN: Avaliação de QoS em Redes de Sensores Sem Fio

Repositório de apoio à dissertação de mestrado **"Avaliação da Qualidade de Serviço (QoS) em Redes de
Sensores Sem Fio: Uma Análise Comparativa dos Protocolos MQTT e MQTT-SN"**, do Programa de
Pós-Graduação em Tecnologia da Informação (PPGTI) do IFPB.

**Autor:** Laerte Bernardo de Medeiros

Os códigos comparam o **MQTT** (TCP) e o **MQTT-SN** (UDP) em latência, *jitter*, vazão (*throughput*),
perda de pacotes e taxa de entrega (PDR), em cenários de comunicação 1:N, N:1 e N:N.

## Estrutura

```
.
├── exp1-simulacao/    # Experimento 1: MQTT × MQTT-SN no CupCarbon
│   ├── publisher-mqtt.py
│   ├── subscriber-mqtt.py
│   ├── publisher-mqttsn.py
│   ├── subscriber-mqttsn.py
│   └── mqttsn/        # biblioteca cliente MQTT-SN
├── exp2-gateway/      # Experimento 2: gateway MQTT-SN independente (em desenvolvimento)
├── exp3-hardware/     # Experimento 3: nós físicos com ESP8266 (em desenvolvimento)
├── resultados/        # Dados brutos e consolidados
├── docs/              # Texto da qualificação
└── README.md
```

| Experimento | Descrição | Situação |
|---|---|---|
| 1 | MQTT × MQTT-SN com RSMB na AWS, como *gateway* integrado (CupCarbon) | Concluído |
| 2 | MQTT-SN com *gateway* independente | Em desenvolvimento |
| 3 | Nós físicos ESP8266 | Em desenvolvimento |

## Arquitetura do Experimento 1

```
 Nós CupCarbon (scripts Python)
   │ MQTT    ── TCP 1883 ─► Mosquitto 2.0.18 (AWS EC2)
   │ MQTT-SN ── UDP 1884 ─► RSMB 1.3.0.2 (AWS EC2, gateway integrado)
```

O Mosquitto e o RSMB são executados cada um em sua própria instância EC2.

QoS 0, *payload* fixo de 70 bytes, janela de envio de 10 s, taxas de 1 a 1000 msg/s,
13 cenários e 10 repetições por cenário.

## Arquitetura do Experimento 2

O RSMB passa a rodar na máquina local, como *gateway* independente, e encaminha as mensagens ao
Mosquitto na AWS por uma ponte (*bridge*) MQTT sobre TCP. A arquitetura do *gateway* é a única variável
alterada em relação ao Experimento 1.

```
 Nós CupCarbon (scripts Python)
   │ MQTT-SN ── UDP 1884 ─► RSMB 1.3.0.2 (local, gateway independente)
                              │ MQTT ── TCP 1883 (bridge)
                              ▼
                            Mosquitto 2.0.18 (AWS EC2)
```

## Requisitos

### Servidor (instâncias AWS EC2)

- Eclipse Mosquitto **2.0.18** (MQTT, porta 1883/TCP)
- RSMB **1.3.0.2** (MQTT-SN, porta 1884/UDP)

### Clientes (máquina que executa o CupCarbon)

- [CupCarbon](https://cupcarbon.com)
- Python 3
- `paho-mqtt` **1.6.1** (*scripts* MQTT): `pip install paho-mqtt==1.6.1`. Os *scripts* usam a API 1.x do Paho,
  incompatível com a versão 2.x.
- `mqttsn` (*scripts* MQTT-SN): [cliente MQTT-SN para Python 3 e MicroPython](https://github.com/ehong-tl/mqttsn-python3-micropython),
  de EH Ong, baseado no cliente de Ian Craggs (IBM, projeto Eclipse), sob as licenças Eclipse Public License v1.0
  e Eclipse Distribution License v1.0. Não é instalado via `pip`: a pasta `mqttsn/` deve ficar no mesmo
  diretório dos *scripts* MQTT-SN.

## Como executar

1. Suba o Mosquitto (porta 1883) e o RSMB (porta 1884), cada um em sua instância na AWS.
2. Ajuste endereço, porta e tópico do *broker* no início de cada *script*.
3. No CupCarbon, associe os *scripts* `publisher-*` e `subscriber-*` do protocolo desejado aos nós.
4. Defina `MENSAGENS_POR_SEGUNDO` conforme o cenário e inicie a simulação.
5. Ao fim da janela, cada assinante imprime o resumo no console do simulador.

### Parâmetros (início dos *scripts*)

| Parâmetro | Onde | Padrão | Descrição |
|---|---|---|---|
| `MENSAGENS_POR_SEGUNDO` | publicadores | `1.0` | Taxa de envio |
| `DURACAO_ENVIO_S` | publicadores | `10.0` | Janela de envio (s) |
| `ATRASO_PRE_ENVIO_S` | publicadores | `4.0` | Espera para sincronizar com os assinantes (s) |
| `TAMANHO_PAYLOAD_FIXO_BYTES` | publicadores | `70` | Tamanho fixo do *payload* |
| `duracao` / `duracao_simulacao` | assinantes MQTT / MQTT-SN | `34.0` / `33.0` | Janela de recepção (s) |

## Métricas

| Métrica | Cálculo |
|---|---|
| Latência | instante de recepção − instante de envio (`ts` no *payload*) |
| *Jitter* | média da variação absoluta entre latências consecutivas (ordem de chegada) |
| PDR | mensagens recebidas / enviadas, pelo identificador sequencial |
| *Throughput* | bytes de *payload* recebidos / intervalo entre a primeira e a última recepção |
