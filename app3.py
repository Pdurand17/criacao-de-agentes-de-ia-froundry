import cv2
import mediapipe as mp
import pyautogui
import numpy as np

# Configuração de segurança do PyAutoGUI
pyautogui.FAILSAFE = True

def iniciar_controle_mouse_invisivel():
    print("🚀 Iniciando rastreamento de mãos em segundo plano...")
    print("💡 Mova o seu dedo indicador para controlar o cursor. Junte o polegar e o indicador para clicar. Pressione Ctrl+C para parar.")

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    cap = cv2.VideoCapture(0)
    screen_width, screen_height = pyautogui.size()

    # Variáveis para controle do clique e suavização
    clicado = False
    
    # Posições anteriores para calcular a suavização (quanto maior o valor, mais suave/lento o movimento)
    suavizacao = 5
    pos_anterior_x, pos_anterior_y = 0, 0

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Erro: Não foi possível aceder à câmera.")
                break

            # Espelha a imagem para o movimento ser natural
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            # Converte para RGB para o MediaPipe processar
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    index_finger = hand_landmarks.landmark[8]
                    thumb_finger = hand_landmarks.landmark[4]
                    
                    # Mapeia as coordenadas normalizadas para a resolução da tela
                    target_x = np.interp(index_finger.x, [0.15, 0.85], [0, screen_width])
                    target_y = np.interp(index_finger.y, [0.15, 0.85], [0, screen_height])

                    # Suavização de movimento (Filtro de interpolação linear)
                    screen_x = pos_anterior_x + (target_x - pos_anterior_x) / suavizacao
                    screen_y = pos_anterior_y + (target_y - pos_anterior_y) / suavizacao

                    # Move o cursor do mouse
                    try:
                        pyautogui.moveTo(screen_x, screen_y, _pause=False)
                    except Exception:
                        pass

                    # Atualiza a posição anterior
                    pos_anterior_x, pos_anterior_y = screen_x, screen_y

                    # Detecção de clique (distância entre polegar e indicador)
                    x1, y1 = int(index_finger.x * w), int(index_finger.y * h)
                    x2, y2 = int(thumb_finger.x * w), int(thumb_finger.y * h)
                    
                    distancia = np.hypot(x2 - x1, y2 - y1)

                    if distancia < 30:
                        if not clicado:
                            pyautogui.click()
                            clicado = True
                    else:
                        clicado = False

    except KeyboardInterrupt:
        print("\n🛑 Controlo de mouse encerrado pelo utilizador.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    iniciar_controle_mouse_invisivel()








