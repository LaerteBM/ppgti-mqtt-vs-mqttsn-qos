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
│   └── subscriber-mqttsn.py
├── exp2-gateway/      # Experimento 2: gateway MQTT-SN independente (em desenvolvimento)
├── exp3-hardware/     # Experimento 3: nós físicos com ESP8266 (em desenvolvimento)
├── resultados/        # Dados brutos e consolidados
├── docs/              # Texto da qualificação
├── requirements.txt
└── README.md
```

| Experimento | Descrição | Situação |
|---|---|---|
| 1 | MQTT × MQTT-SN com RSMB local encaminhando ao Mosquitto na AWS (CupCarbon) | Concluído |
| 2 | MQTT-SN com *gateway* independente | Em desenvolvimento |
| 3 | Nós físicos ESP8266 | Em desenvolvimento |

## Arquitetura do Experimento 1

```
 Nós CupCarbon (scripts Python)
   │ MQTT    ── TCP 1883 ────────────► Mosquitto 2.0.18 (AWS EC2)
   │ MQTT-SN ── UDP 1884 ─► RSMB 1.3.0.2 (local) ─► Mosquitto 2.0.18 (AWS EC2)
```

QoS 0, *payload* fixo de 70 bytes, janela de envio de 10 s, taxas de 1 a 1000 msg/s,
13 cenários e 10 repetições por cenário.

## Requisitos

- Python 3 e `pip install -r requirements.txt`
- [CupCarbon](https://cupcarbon.com)
- Eclipse Mosquitto **2.0.18**
- RSMB **1.3.0.2**

## Como executar

1. Suba o Mosquitto (porta 1883) e o RSMB (porta 1884, com ponte para o Mosquitto).
2. Ajuste endereço, porta e tópico do *broker* no início de cada *script*.
3. No CupCarbon, associe os *scripts* `publisher-*` e `subscriber-*` do protocolo desejado aos nós.
4. Defina `MENSAGENS_POR_SEGUNDO` conforme o cenário e inicie a simulação.
5. Ao fim da janela, cada assinante imprime o resumo no console do simulador.

A comunicação com o CupCarbon usa a saída padrão: `getid` solicita o identificador do nó e `print ...`
exibe mensagens no console.

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

## Licença

A definir.
