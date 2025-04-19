import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import cv2
import mediapipe as mp
import numpy as np
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
from fastapi.responses import HTMLResponse
from pdf2image import convert_from_path
from fastapi.responses import FileResponse
from PyPDF2 import PdfReader

app = FastAPI()

# Inicializamos mediapipe para la detección de manos
mp_hands = mp.solutions.hands
# hands = mp_hands.Hands()
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Configurar el logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lista para mantener los gestos actuales
current_gesture = ""

def count_extended_fingers(landmarks):
    tips = [8, 12, 16, 20]  # Índices de las puntas (sin pulgar)
    base = [6, 10, 14, 18]  # Juntas más cercanas a la palma
    count = 0
    for tip, b in zip(tips, base):
        if landmarks[tip][1] < landmarks[b][1]:  # dedo extendido
            count += 1
    return count

def is_thumb_up(landmarks):
    # Detectar si el pulgar está arriba comparado con el nudillo
    return landmarks[4][1] < landmarks[2][1]  # y menor es más arriba

def detect_hand_gesture(landmarks):
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    finger_count = count_extended_fingers(landmarks)

    if is_thumb_up(landmarks):
        return "pulgar arriba"
    elif finger_count == 0:
        return "puño"
    elif finger_count >= 4:
        return "palma"
    elif thumb_tip[0] > index_tip[0]:
        return "dedo izquierda"
    elif thumb_tip[0] < index_tip[0]:
        return "dedo derecha"
    else:
        return "desconocido"

@app.websocket("/ws/gestures")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        if current_gesture:
            await websocket.send_text(current_gesture)  # Enviar el gesto detectado al frontend
        await asyncio.sleep(2)

# Función para generar video con detección de gestos de la mano
def gen_frames():
    cap = cv2.VideoCapture(0)  # Abrir la cámara
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Voltear el frame horizontalmente para corregir la inversión
        frame = cv2.flip(frame, 1)

        # Convertir la imagen a RGB para mediapipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        # Detección de gestos de la mano
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                landmarks = [(landmark.x, landmark.y, landmark.z) for landmark in hand_landmarks.landmark]
                gesture = detect_hand_gesture(landmarks)
                
                # Mostrar el gesto detectado
                if gesture:
                    cv2.putText(frame, f"Gesto: {gesture}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    logger.info(f"Gesture detected: {gesture}")  # Log the gesture
                
                # Actualizar el gesto actual
                global current_gesture
                current_gesture = gesture

                # Dibujar los puntos de la mano
                for landmark in hand_landmarks.landmark:
                    x = int(landmark.x * frame.shape[1])
                    y = int(landmark.y * frame.shape[0])
                    cv2.circle(frame, (x, y), 2, (0, 0, 255), -1)

        # Codificar el frame como JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n') 

@app.get("/get_pdf_page/{page_number}")
def get_pdf_page(page_number: int):
    # Convertir una sola página del PDF en imagen
    # Get the current path
    if (page_number < 1):
        return {"error": "Page number must be greater than 0"}
    current_path = Path(__file__).parent.resolve()
    logger.info(f"Current path: {current_path}")

    image_dir = os.path.join(current_path, "static", "tmp")
    os.makedirs(image_dir, exist_ok=True)

    pdf_path = os.path.join(current_path, "static", "sample.pdf")
    
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    if page_number > total_pages:
        return {"error": "Página fuera de rango"}

    images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number, size=(600, 800))

    # Guardar la imagen temporalmente en el servidor
    image_path = os.path.join(image_dir, f"page_{page_number}.jpg")
    images[0].save(image_path, "JPEG")

    return FileResponse(image_path)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/video")
def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

@app.get("/get_total_pages")
def get_total_pages():
    current_path = Path(__file__).parent.resolve()
    pdf_path = os.path.join(current_path, "static", "sample.pdf")
    reader = PdfReader(pdf_path)
    return {"total_pages": len(reader.pages)}

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
