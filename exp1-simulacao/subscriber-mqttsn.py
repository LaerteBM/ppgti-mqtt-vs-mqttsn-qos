import time
import json
import sys
import math
from collections import deque
from mqttsn.MQTTSNclient import Client, Callback

# Função para interagir com o CupCarbon
def cup(com):
    print(com, flush=True)

# Define ID do nó
cup("getid")
node_id = input()
CLIENT_ID = f"cup-sub-{node_id}"

# Configurações do broker RSMB (IP atualizado conforme solicitado)
BROKER_HOST = "127.0.0.1" 
BROKER_PORT = 1884
TOPIC = "wsn/data"

# Variáveis para métricas
dados_coletados = []
fila_processamento = deque()
duracao_simulacao = 33.0

def obter_timestamp_ms():
    return int(time.time() * 1000)

# Callback personalizado com Fila de Processamento
class MyCallback(Callback):
    def messageArrived(self, topicName, payload, qos, retained, msgid):
        # Captura o tempo de chegada IMEDIATAMENTE
        ts_recebimento = obter_timestamp_ms()
        # Joga na fila para processamento posterior
        fila_processamento.append((payload, ts_recebimento))

def processar_fila():
    global dados_coletados
    while fila_processamento:
        payload_bruto, ts_rec = fila_processamento.popleft()
        try:
            if isinstance(payload_bruto, bytes):
                payload_str = payload_bruto.decode('utf-8')
            else:
                payload_str = payload_bruto
            
            payload_size = len(payload_str)
            obj = json.loads(payload_str)
            
            # Mapeamento correspondente às chaves curtas recebidas
            ts_env = obj.get("ts", 0)
            msg_id = obj.get("id", -1)
            temp = obj.get("t", 0)
            umidade = obj.get("u", 0)
            luminosidade = obj.get("l", 0)
            
            delay = ts_rec - ts_env
            
            dados_coletados.append([msg_id, temp, ts_env, ts_rec, delay, payload_size, luminosidade, umidade])
            
            # Feedback visual para saber que mensagens estão chegando
            if msg_id % 5 == 0:
                cup(f"print .") 

        except Exception:
            pass

def calcular_jitter(lista):
    if len(lista) < 2: return 0.0
    latencias = [d[4] for d in lista]
    soma = sum(math.fabs(latencias[i] - latencias[i-1]) for i in range(1, len(latencias)))
    return round(soma / (len(latencias) - 1), 2)

def exibir_relatorio():
    # Limpeza final da fila
    processar_fila() 
    
    total = len(dados_coletados)
    lat_media = 0.0
    jitter = 0.0
    throughput = 0.0
    
    if total > 0:
        lat_media = round(sum(d[4] for d in dados_coletados) / total, 2)
        jitter = calcular_jitter(dados_coletados)
        
        # Ordena para garantir cálculos de tempo precisos
        dados_coletados.sort(key=lambda x: x[3])
        
        ts_inicio = dados_coletados[0][3]
        ts_fim = dados_coletados[-1][3]
        tempo_s = (ts_fim - ts_inicio) / 1000.0
        
        if tempo_s <= 0: tempo_s = 0.001
        
        total_bytes = sum(d[5] for d in dados_coletados)
        throughput = round(total_bytes / tempo_s, 2)

    # Formatação reforçada para garantir que apareça no CupCarbon
    cup(f"print RESUMO_MQTTSN: REC={total} | LAT={lat_media}ms | JIT={jitter}ms | TP={throughput}Bps")
    # Pequeno delay para o CupCarbon processar a linha de log antes do script morrer
    time.sleep(2.0)

# --- EXECUÇÃO ---

callback = MyCallback()
client = Client(clientid=CLIENT_ID, host=BROKER_HOST, port=BROKER_PORT)
client.registerCallback(callback)

try:
    cup(f"print Conectando ao RSMB em {BROKER_HOST}...")
    client.connect()
    rc, topic_id = client.subscribe(TOPIC)
    
    tempo_limite = time.monotonic() + duracao_simulacao
    cup(f"print *** MQTT-SN ATIVO POR {duracao_simulacao}s ***")

    while time.monotonic() < tempo_limite:
        processar_fila()
        time.sleep(0.05) # Delay leve para não saturar CPU, mas manter processamento vivo

    # EXIBIÇÃO DO RELATÓRIO ANTES DE DESCONECTAR
    exibir_relatorio()
    
    client.disconnect()

except Exception as e:
    cup(f"print ERRO: {e}")
    sys.exit(1)
