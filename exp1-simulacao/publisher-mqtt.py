import time
import json 
import random
import sys
from paho.mqtt import client as mqtt_client

# Funcao para interagir com o CupCarbon
def cup(comando):
    # Garante que o comando é enviado imediatamente
    print(comando, flush=True)

# Mapeamento de códigos de erro de conexão MQTT
def obter_descricao_erro(rc):
    # Trata o código de erro (int) corretamente para Paho 1.x
    try:
        rc_int = int(rc)
    except:
        rc_int = -99
            
    return {
        0: "Conexão bem-sucedida!",
        1: "Versão de protocolo incorreta.",
        2: "Identificador de cliente inválido.",
        3: "Servidor indisponível (Verifique o broker/EC2/IP).",
        4: "Usuário ou senha inválido.",
        5: "Não autorizado (Verifique as permissões/Security Group da AWS).",
    }.get(rc_int, f"Erro desconhecido: {rc}")

# Define o ID do cliente
cup("getid")
identificador = input()
id_cliente = "cup-pub-" + identificador

# Configuracoes de conexao com o broker
endereco_broker = "18.228.220.124" 
porta = 1883
topico = "wsn/temperature"
nvl_qos = 0

# --- PARAMETROS DE ENVIO SIMPLIFICADOS ---
MENSAGENS_POR_SEGUNDO = 1.0  # Taxa desejada de mensagens por segundo
DURACAO_ENVIO_S = 10.0       # Tempo total da janela de envio (em segundos)
ATRASO_PRE_ENVIO_S = 4.0     # Tempo de espera antes de começar a enviar (Sincronização)

# --- PARAMETRO DE PAYLOAD ---
TAMANHO_PAYLOAD_FIXO_BYTES = 70  # Define o tamanho fixo (em bytes) do payload
# -------------------------------------------

# CALCULA OS PARÂMETROS NECESSÁRIOS
total_mensagens = int(MENSAGENS_POR_SEGUNDO * DURACAO_ENVIO_S)
if MENSAGENS_POR_SEGUNDO > 0:
    intervalo_entre_mensagens_s = 1.0 / MENSAGENS_POR_SEGUNDO
else:
    intervalo_entre_mensagens_s = 0.0

# Funcao para obter o timestamp em milissegundos
def obter_timestamp_ms():
    return int(time.time() * 1000)

# Funcao para conectar ao servidor 
def conectar_mqtt():
    # Callback adaptado para Paho-MQTT v1.x (assinatura sem 'properties')
    def ao_conectar(cliente, dados_usuario, flags, rc): 
        descricao_erro = obter_descricao_erro(rc)
        if rc == 0:
            cup("print Conectado!")
        else:
            cup(f"print Falha ao conectar! Erro rc={rc}: {descricao_erro}")
            sys.exit(1) 

    # Inicialização compatível com a versão instalada no seu ambiente (Paho 1.x)
    cliente = mqtt_client.Client(client_id=id_cliente)
    cliente.on_connect = ao_conectar
    
    cup(f"print Tentando conectar o PUBLISHER a {endereco_broker}:{porta}...")
    try:
        cliente.connect(endereco_broker, porta, keepalive=20) 
    except Exception as e:
        cup(f"print ERRO DE REDE/TIMEOUT: Não foi possível alcançar o broker. Detalhes: {e}")
        sys.exit(1)
        
    return cliente

# Funcao para publicar mensagens
def publicar(cliente: mqtt_client):
    mensagens_enviadas = 0
    
    cup(f"print AGUARDANDO {ATRASO_PRE_ENVIO_S}s p/ iniciar o envio (Sincronizacao)...")
    cup(f"print ENVIO: {total_mensagens} msgs em {DURACAO_ENVIO_S}s (Taxa: {MENSAGENS_POR_SEGUNDO} pps | Intervalo: {intervalo_entre_mensagens_s:.3f}s)")
    cup(f"print PAYLOAD: {TAMANHO_PAYLOAD_FIXO_BYTES} Bytes (Fixo)")

    time.sleep(ATRASO_PRE_ENVIO_S) 
    
    # Inicia o rastreamento do tempo de início da janela de envio
    tempo_inicio_envio = time.monotonic()
    
    for i in range(total_mensagens):
        # --- AGENDAMENTO OTIMIZADO (COMPENSAÇÃO DE DRIFT) ---
        tempo_alvo = tempo_inicio_envio + (i * intervalo_entre_mensagens_s)
        
        # GERAÇÃO DOS DADOS SIMULADOS DE TELEMETRIA IoT
        temp = round(random.uniform(25.0, 35.0), 2)
        luminosidade = random.randint(1, 65535)
        umidade = random.randint(0, 100)
        
        # JSON formatado de forma enxuta com chaves curtas e sem espaços extras
        payload_obj = {
            "id": i + 1, 
            "t": temp,
            "ts": obter_timestamp_ms(),
            "l": luminosidade,
            "u": umidade
        }
        payload_json = json.dumps(payload_obj, separators=(',', ':'))
        
        # LÓGICA DE TAMANHO FIXO (PADDING)
        payload_size = len(payload_json)
        if payload_size > TAMANHO_PAYLOAD_FIXO_BYTES:
            cup(f"print AVISO: Mensagem ID:{i + 1} ({payload_size}B) excedeu o limite fixo de {TAMANHO_PAYLOAD_FIXO_BYTES}B.")
            payload = payload_json
        else:
            padding_necessario = TAMANHO_PAYLOAD_FIXO_BYTES - payload_size
            payload = payload_json + (" " * padding_necessario)
        
        resultado = cliente.publish(topico, payload, qos=nvl_qos)
        status = resultado[0]
        
        if status == 0:
            mensagens_enviadas += 1
            cup(f"print ENVIADO (ID:{i + 1} | SIZE:{len(payload)}B | TS_ALVO:{tempo_alvo:.3f}): {payload[:20]}...")
        else:
            cup(f"print FALHA AO ENVIAR MENSAGEM ID:{i + 1}")

        # CORREÇÃO DE TEMPO (DORMINDO SÓ O NECESSÁRIO)
        tempo_restante = tempo_alvo - time.monotonic()
        if tempo_restante > 0:
            time.sleep(tempo_restante)

    cup(f"print PUBLISHER_FINAL: TOTAL_ENVIADO:{mensagens_enviadas}/TOTAL_ESPERADO:{total_mensagens}")
    time.sleep(0.5)
    cliente.disconnect()

# Funcao principal
def executar():
    cliente = conectar_mqtt()
    cliente.loop_start() 
    time.sleep(1)
    publicar(cliente)
    cliente.loop_stop()

if __name__ == '__main__':
    executar()
