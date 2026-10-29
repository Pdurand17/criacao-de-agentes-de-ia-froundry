import os
import cv2
from openai import AzureOpenAI
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações da Azure OpenAI obtidas do ambiente
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01-preview")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5")

def inicializar_cliente():
    """Inicializa e retorna o cliente da Azure OpenAI."""
    if not ENDPOINT or not API_KEY:
        raise ValueError("Erro: As variáveis de ambiente AZURE_OPENAI_ENDPOINT e AZURE_OPENAI_API_KEY precisam estar configuradas.")
    
    return AzureOpenAI(
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version=API_VERSION
    )

def capturar_frame_camera():
    """Abre a webcam, exibe o feed e captura um frame quando a barra de espaço for pressionada."""
    # Inicializa a webcam padrão (índice 0)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        raise RuntimeError("Erro: Não foi possível acessar a webcam.")

    print("\n[INFO] Câmera iniciada.")
    print("[INFO] Pressione 'ESPAÇO' para capturar a imagem ou 'ESC' para sair.\n")

    frame_capturado = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERRO] Falha ao capturar imagem da câmera.")
                break

            # Mostra o vídeo na tela em tempo real
            cv2.imshow("Agente de Visao - Azure OpenAI (Pressione ESPACO para capturar)", frame)

            tecla = cv2.waitKey(1) & 0xFF
            
            # Tecla ESC (27) para sair sem capturar
            if tecla == 27:
                print("[INFO] Operação cancelada pelo usuário.")
                break
            
            # Tecla ESPAÇO (32) para capturar o frame atual
            elif tecla == 32:
                frame_capturado = frame
                print("[SUCESSO] Frame capturado com sucesso!")
                # Salva temporariamente a imagem capturada em disco
                caminho_temp = "temp_capture.jpg"
                cv2.imwrite(caminho_temp, frame_capturado)
                break
    finally:
        # Libera a câmera e fecha as janelas abertas
        cap.release()
        cv2.destroyAllWindows()

    return caminho_temp if frame_capturado is not None else None

def analisar_imagem_com_azure(caminho_imagem):
    """Envia a imagem capturada para o modelo na Azure OpenAI para análise descritiva."""
    import base64

    print("[INFO] Conectando à Azure OpenAI e processando a imagem...")

    try:
        client = inicializar_cliente()

        # Converte a imagem para base64 para envio via API
        with open(caminho_imagem, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

        # Requisição multimodal para o modelo
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente de IA especialista em visão computacional. Descreva detalhadamente o que pode ser visto na imagem fornecida, destacando objetos, pessoas, ambiente e contexto geral de forma clara e objetiva em português."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Por favor, analise esta imagem capturada da minha webcam e me dê uma descrição detalhada do que você vê."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                        }
                    ]
                }
            ],
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Ocorreu um erro ao comunicar com a API da Azure OpenAI: {str(e)}"
    
    finally:
        # Remove o arquivo temporário de imagem após o uso
        if os.path.exists(caminho_imagem):
            os.remove(caminho_imagem)

def main():
    print("=== AGENTE DE VISÃO ARTIFICIAL AZURE OPENAI ===")
    
    # Passo 1: Capturar imagem da câmera
    caminho_imagem = capturar_frame_camera()
    
    if caminho_imagem:
        # Passo 2: Enviar para o modelo e obter a descrição
        descricao = analisar_imagem_com_azure(caminho_imagem)
        
        print("\n" + "="*40)
        print("DESCRIÇÃO DA IMAGEM PELO MODELO:")
        print("="*40)
        print(descricao)
        print("="*40 + "\n")

if __name__ == "__main__":
    main()