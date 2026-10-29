import cv2
import mediapipe as mp
import pyautogui
import numpy as np


# Configuração de segurança do PyAutoGUI (mova o mouse para o canto da tela para travar se necessário)
pyautogui.FAILSAFE = True


def iniciar_controle_mouse_invisivel():
    print("🚀 Iniciando rastreamento de mãos em segundo plano...")
    print("💡 Mova o seu dedo indicador para controlar o cursor. Pressione Ctrl+C no terminal para parar.")


    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )


    cap = cv2.VideoCapture(0)
    screen_width, screen_height = pyautogui.size()


    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Erro: Não foi possível aceder à câmara.")
                break


            # Espelha a imagem para o movimento ser natural
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            # Converte para RGB para o MediaPipe processar
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)


            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Pega as coordenadas da ponta do dedo indicador (Landmark 8)
                    index_finger = hand_landmarks.landmark[8]
                    
                    # Mapeia as coordenadas normalizadas (0.0 a 1.0) para a resolução da tela
                    screen_x = np.interp(index_finger.x, [0.15, 0.85], [0, screen_width])
                    screen_y = np.interp(index_finger.y, [0.15, 0.85], [0, screen_height])


                    # Move o cursor do mouse instantaneamente sem atraso e sem mostrar janelas
                    try:
                        pyautogui.moveTo(screen_x, screen_y, _pause=False)
                    except Exception:
                        pass


    except KeyboardInterrupt:
        print("\n🛑 Controlo de mouse encerrado pelo utilizador.")
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    iniciar_controle_mouse_invisivel()