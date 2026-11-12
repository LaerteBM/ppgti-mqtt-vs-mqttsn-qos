import time
import json 
import random
import sys
from mqttsn.MQTTSNclient import Client, Callback

# Funcao para interagir com o CupCarbon
def cup(comando):
    print(comando, flush=True)

# Pega o ID do nó no CupCarbon
cup("getid")
node_id = input()
client_id = f"cup-pub-{node_id}"

# Configuração do broker MQTT-SN (usando IP e porta do seu exemplo)
broker_ip = "127.0.0.1" 
broker_port = 1884
topic = "wsn/data"
qos = 0

# --- PARAMETROS DE ENVIO SIMPLIFICADOS ---
MENSAGENS_POR_SEGUNDO = 1.0  # Taxa desejada de mensagens por segundo
DURACAO_ENVIO_S = 10.0       # Tempo total da janela de envio (em segundos)
ATRASO_PRE_ENVIO_S = 4.0     # Tempo de espera antes de começar a enviar (Sincronização)

# --- PARAMETRO DE PAYLOAD ---
TAMANHO_PAYLOAD_FIXO_BYTES = 70  # Define o tamanho fixo (em bytes) do payload
# Se o payload for menor, será preenchido com espaços.
# -------------------------------------------

# CALCULA OS PARÂMETROS NECESSÁRIOS
total_mensagens = int(MENSAGENS_POR_SEGUNDO * DURACAO_ENVIO_S)
if MENSAGENS_POR_SEGUNDO > 0:
    # Calcula o intervalo necessário para atingir a taxa de msgs/s
    intervalo_entre_mensagens_s = 1.0 / MENSAGENS_POR_SEGUNDO
else:
    intervalo_entre_mensagens_s = 0.0

# Funcao para obter o timestamp em milissegundos
def obter_timestamp_ms():
    return int(time.time() * 1000)

# Callback padrão (necessário, mas não usado ativamente no Pub Qos=0)
class MyCallback(Callback):
    def deliveryComplete(self, msgid):
        pass # Não faz nada para QoS 0

def run():
    client = Client(client_id, host=broker_ip, port=broker_port)
    client.registerCallback(MyCallback())

    try:
        cup(f"print Tentando conectar o PUBLISHER a {broker_ip}:{broker_port}...")
        client.connect()
        cup("print Conectado com sucesso!")

        # Registrar tópico (necessário para MQTT-SN)
        cup(f"print Tentando registrar tópico '{topic}'...")
        topic_id = client.register(topic)
        cup(f"print Tópico registrado! TopicId: {topic_id}")

        # 1. Espera explícita para garantir que o Subscriber tenha se inscrito
        cup(f"print AGUARDANDO {ATRASO_PRE_ENVIO_S}s p/ iniciar o envio (Sincronizacao)...")
        cup(f"print ENVIO: {total_mensagens} msgs em {DURACAO_ENVIO_S}s (Taxa: {MENSAGENS_POR_SEGUNDO} pps | Intervalo: {intervalo_entre_mensagens_s:.3f}s)")
        cup(f"print PAYLOAD: {TAMANHO_PAYLOAD_FIXO_BYTES} Bytes (Fixo)")

        time.sleep(ATRASO_PRE_ENVIO_S) 

        # Inicia o rastreamento do tempo de início da janela de envio
        tempo_inicio_envio = time.monotonic()

        mensagens_enviadas = 0

        # 2. Loop de envio
        for i in range(total_mensagens):

            # --- AGENDAMENTO OTIMIZADO (COMPENSAÇÃO DE DRIFT) ---
            tempo_alvo = tempo_inicio_envio + (i * intervalo_entre_mensagens_s)

            # Gera dados (temperatura, umidade, luminosidade, ID sequencial e timestamp)
            temp = round(random.uniform(25.0, 35.0), 2)
            umidade = round(random.uniform(50.0, 70.0), 2)
            luminosidade = round(random.uniform(200.0, 800.0), 2)

            payload_obj = {
                "id": i + 1, # ID sequencial (começa em 1)
                "t": temp,
                "u": umidade,
                "l": luminosidade,
                "ts": obter_timestamp_ms()
            }

            payload_json = json.dumps(payload_obj)

            # --- LÓGICA DE TAMANHO FIXO (PADDING) ---
            payload_size = len(payload_json)

            if payload_size > TAMANHO_PAYLOAD_FIXO_BYTES:
                cup(f"print AVISO: Mensagem ID:{i + 1} ({payload_size}B) excedeu o limite fixo de {TAMANHO_PAYLOAD_FIXO_BYTES}B.")
                payload = payload_json
            else:
                padding_necessario = TAMANHO_PAYLOAD_FIXO_BYTES - payload_size
                payload = payload_json + (" " * padding_necessario)
            # ----------------------------------------

            # Publica
            client.publish(topic_id, payload.encode('utf-8'), qos=qos)
            mensagens_enviadas += 1
            cup(f"print ENVIADO (ID:{i + 1} | SIZE:{len(payload)}B | TS_ALVO:{tempo_alvo:.3f}): {payload[:20]}...")

            # --- CORREÇÃO DE TEMPO (DORMINDO SÓ O NECESSÁRIO) ---
            tempo_restante = tempo_alvo - time.monotonic()
            if tempo_restante > 0:
                time.sleep(tempo_restante)

        # 3. Impressão final compacta
        cup(f"print PUBLISHER_FINAL: TOTAL_ENVIADO:{mensagens_enviadas}/TOTAL_ESPERADO:{total_mensagens}")

    except Exception as e:
        cup(f"print ERRO: {e}")

    finally:
        try:
            client.disconnect()
            cup("print Desconectado do broker.")
        except:
            pass

if __name__ == "__main__":
    run()
