# Importacao das bibliotecas
from paho.mqtt import client as mqtt_client
import time
import json 
import sys
import math # Necessário para a função math.fabs

# Funcao para interagir com o CupCarbon
def cup(comando):
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
        4: "Usuário ou senha inválidos.",
        5: "Não autorizado (Verifique as permissões/Security Group da AWS).",
    }.get(rc_int, f"Erro desconhecido: {rc}")

# Define o ID do cliente
cup("getid")
identificador = input()
id_cliente = "cup-sub-" + identificador

# Configuracoes de conexao com o broker - IP ATUALIZADO
endereco_broker = "18.228.220.124" 
porta = 1883
topico = "wsn/temperature"
nvl_qos = 0   

# --- PARAMETRO DE SIMULACAO ---
# Duração total da janela de conexão (cobre o atraso do Publisher e o tempo de envio)
duracao = 34.0 
# -------------------------------

# VARIÁVEIS GLOBAIS PARA COLETA DE DADOS
dados_coletados = [] 

# Funcao para obter o timestamp em milissegundos
def obter_timestamp_ms():
    return int(time.time() * 1000)

# FUNÇÃO AUXILIAR PARA CALCULAR O JITTER
def calcular_jitter_medio(lista_dados):
    if len(lista_dados) < 2:
        return 0.0 

    latencias = [dado[4] for dado in lista_dados]
    soma_variacao_absoluta = 0
    
    for i in range(1, len(latencias)):
        delay_atual = latencias[i]
        delay_anterior = latencias[i-1]
        variacao_absoluta = math.fabs(delay_atual - delay_anterior)
        soma_variacao_absoluta += variacao_absoluta
        
    numero_de_variacoes = len(latencias) - 1
    jitter_medio = soma_variacao_absoluta / numero_de_variacoes
    return round(jitter_medio, 2)

# Funcao para exibir o relatório final no console do CupCarbon
def exibir_relatorio_console(cliente):
    global dados_coletados
    mensagens_recebidas = len(dados_coletados)
    
    latencia_media_ms = 0.0
    jitter_medio_ms = 0.0
    throughput_bps = 0.0
    
    if mensagens_recebidas > 0:
        # 1. LATÊNCIA MÉDIA
        latencia_total = sum(dado[4] for dado in dados_coletados)
        latencia_media_ms = round(latencia_total / mensagens_recebidas, 2)

        # 2. JITTER MÉDIO
        jitter_medio_ms = calcular_jitter_medio(dados_coletados)
        
        # 3. CÁLCULO DA DURAÇÃO DE TRANSMISSÃO EFETIVA
        ts_recebimento_primeiro = dados_coletados[0][3]
        ts_recebimento_ultimo = dados_coletados[-1][3]
        tempo_transmissao_ms = ts_recebimento_ultimo - ts_recebimento_primeiro
        tempo_transmissao_s = tempo_transmissao_ms / 1000.0 if tempo_transmissao_ms > 0 else 0.001 
        
        # 4. THROUGHPUT (Bps)
        tamanho_payload_total_bytes = sum(dado[5] for dado in dados_coletados)
        throughput_bps = round(tamanho_payload_total_bytes / tempo_transmissao_s, 2)
    
    resumo_header = (
        f"RESUMO FINAL: RECEBIDAS={mensagens_recebidas} | LAT_MEDIA={latencia_media_ms}ms | "
        f"JITTER_MEDIA={jitter_medio_ms}ms | "
        f"THROUGHPUT_BPS={throughput_bps}Bps"
    )
    
    relatorio_final_concatenado = f"JANELA ENCERRADA. {resumo_header}"
    cup(f"print {relatorio_final_concatenado}")
    
    time.sleep(1)
    if cliente.is_connected():
        cliente.disconnect()

# Funcao para conectar ao servidor 
def conectar_mqtt():
    # Callback adaptado para Paho-MQTT v1.x (sem o parâmetro 'properties')
    def ao_conectar(cliente, dados_usuario, flags, rc): 
        descricao_erro = obter_descricao_erro(rc)
        if rc == 0:
            cup("print Conectado!")
            assinar(cliente)
        else:
            cup(f"print Falha ao conectar! Erro rc={rc}: {descricao_erro}")
            sys.exit(1)

    # Inicialização compatível com Paho v1.x
    cliente = mqtt_client.Client(client_id=id_cliente)
    cliente.on_connect = ao_conectar
    
    cup(f"print Tentando conectar o SUBSCRIBER a {endereco_broker}:{porta}...")
    try:
        cliente.connect(endereco_broker, porta, keepalive=20) 
    except Exception as e:
        cup(f"print ERRO DE REDE/TIMEOUT: Detalhes: {e}")
        sys.exit(1)
        
    return cliente

# Funcao para se inscrever em um topico
def assinar(cliente: mqtt_client):
    def ao_receber_mensagem(cliente, dados_usuario, msg):
        global dados_coletados
        time_recebimento_ms = obter_timestamp_ms()
        
        try:
            payload_bytes = msg.payload 
            payload_size_bytes = len(payload_bytes)
            mensagem_obj = json.loads(payload_bytes.decode())
            
            # MAPEAMENTO EXATO: Lendo as chaves do Publisher enviado
            time_envio_ms = mensagem_obj.get("ts", 0)
            temperatura = mensagem_obj.get("t", "N/A")
            msg_id = mensagem_obj.get("id", -1)
            luminosidade = mensagem_obj.get("l", "N/A") 
            umidade = mensagem_obj.get("u", "N/A")
            
            delay_ms = time_recebimento_ms - time_envio_ms
            
            # Insere as novas variáveis no fim da lista para manter os índices estatísticos intactos
            dados_coletados.append([msg_id, temperatura, time_envio_ms, time_recebimento_ms, delay_ms, payload_size_bytes, luminosidade, umidade])
            cup(f"print RECEBIDO (ID:{msg_id} - Latência: {delay_ms} ms - Tamanho: {payload_size_bytes} B)")

        except json.JSONDecodeError:
            cup("print ERRO: JSON inválido.")
        except Exception as e:
            cup(f"print ERRO NO PROCESSAMENTO: {e}")

    cliente.subscribe(topico, qos=nvl_qos)
    cliente.on_message = ao_receber_mensagem

# Funcao principal
def executar():
    cliente = conectar_mqtt()
    if cliente is None: return
    
    tempo_limite = time.monotonic() + duracao
    cup(f"print *** RECEBIMENTO INICIADO. JANELA DE MEDIÇÃO DE {duracao}s ATIVA ***")
    
    while time.monotonic() < tempo_limite:
        rc = cliente.loop(timeout=0.1) 
        if rc != 0:
            cup(f"print ERRO DE REDE NO LOOP (rc={rc}).")
            break
            
    exibir_relatorio_console(cliente)

if __name__ == '__main__':
    executar()
