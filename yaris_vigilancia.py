import cv2
import numpy as np
import time
import os
import threading
import logging
import requests
import datetime
import firebase_admin
from firebase_admin import credentials, messaging, db

import json

# --- CONFIGURACIÓN TITÁN v8.3 (TRIPLE ESCUDO + JSON) ---
if not os.path.exists("respaldos_json"): os.makedirs("respaldos_json")

# --- CONTROL DE SATURACIÓN Y MERODEO ---
last_alert_times = {} 
suspicion_levels = {} 
notified_sessions = {} 
COOLDOWN_ALERTAS = 120 
UMBRAL_MERODEO = 2 # Bajado para pruebas rápidas

def respaldo_json_seguro(datos):
    try:
        fecha = datetime.datetime.now().strftime("%Y-%m-%d")
        path = f"respaldos_json/log_{fecha}.json"
        with open(path, "a") as f:
            json.dump(datos, f)
            f.write("\n")
        logging.info("💾 Respaldo JSON guardado.")
    except: pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# --- CREDENCIALES ---
CAM_USER = "admin"
CAM_PASS = "admin"
PB_USER = "josuehg59@gmail.com"
PB_PASS = "Josue800401"

IP_CAMS = "192.168.100.152"
BASE_PB = "http://192.168.100.144:8090/api/collections"

MOVEMENT_THRESHOLD = 600 # Un poco más alto para evitar ruido
COOLDOWN_SECONDS = 30
BUFFER_SIZE = 75

# Inicializar Detector de Personas (Calibrado para ser más estricto)
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

# --- FIREBASE ---
FIREBASE_READY = False
if os.path.exists("firebase_key.json"):
    try:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
        FIREBASE_READY = True
        logging.info("✅ Firebase Conectado.")
    except: pass

# -------------------------------------------------
# LIMPIEZA AUTOMÁTICA (12 HORAS)
# -------------------------------------------------
def conserje_titan():
    while True:
        try:
            logging.info("🧹 Conserje Titán: Iniciando LIMPIEZA PROFUNDA...")
            
            # 1. Login para permisos
            r_auth = requests.post(f"http://192.168.100.144:8090/api/admins/auth-with-password", 
                                  json={"identity": PB_USER, "password": PB_PASS}, timeout=5)
            token = r_auth.json().get("token", "")
            headers = {"Authorization": token}
            
            ahora_dt = datetime.datetime.now(datetime.timezone.utc)
            limite_nube = (ahora_dt - datetime.timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 2. Limpieza de Nube (12 horas)
            for coleccion in ["videos_yaris", "alertas_yaris", "mensajes"]:
                url = f"{BASE_PB}/{coleccion}/records?filter=(created<'{limite_nube}')&perPage=100"
                r = requests.get(url, headers=headers, timeout=10)
                items = r.json().get("items", [])
                for item in items:
                    requests.delete(f"{BASE_PB}/{coleccion}/records/{item['id']}", headers=headers, timeout=5)
            
            # 3. Limpieza de PC (5 días)
            limite_pc = time.time() - (5 * 24 * 3600)
            for folder in ["grabaciones", "respaldos_json"]:
                if os.path.exists(folder):
                    for f in os.listdir(folder):
                        fp = os.path.join(folder, f)
                        if os.path.getmtime(fp) < limite_pc:
                            os.remove(fp)
            
            logging.info("✅ LIMPIEZA PROFUNDA COMPLETADA.")
        except Exception as e:
            logging.warning(f"⚠️ Error en limpieza: {e}")
        
        time.sleep(3600) # Una vez cada hora

threading.Thread(target=conserje_titan, daemon=True).start()

# -------------------------------------------------
# GESTIÓN DE ALERTAS INTELIGENTES
# -------------------------------------------------
def procesar_alerta_con_video(canal, buffer_video):
    try:
        logging.info(f"🚀 INICIANDO PROCESO: Cámara {canal}...")
        # --- ANÁLISIS DE SOSPECHA (MERODEO) ---
        es_yaris = canal in [1, 2]
        
        # Análisis de alta precisión
        frame_analisis = cv2.resize(buffer_video[-1], (640, 480))
        boxes, weights = hog.detectMultiScale(frame_analisis, winStride=(4, 4), padding=(8, 8), scale=1.05)
        
        humano_detectado = False
        if len(weights) > 0:
            logging.info(f"🧐 Objetos en vista. Pesos: {[round(float(w),2) for w in weights]}")
            
        humano_detectado = False
        for i, w in enumerate(weights):
            if w > 0.6: # FILTRO SELECTIVO PARA HUMANOS
                (x, y, w_box, h_box) = boxes[i]
                proporcion = h_box / float(w_box)
                if proporcion > 1.2: 
                    humano_detectado = True
                    logging.info(f"👤 HUMANO CONFIRMADO (Cam {canal}): Confianza {w:.2f}")
                    break
        
        if not humano_detectado:
            suspicion_levels[canal] = 0
            notified_sessions[canal] = False
            return

        # --- PROTOCOLO NOCTURNO TITÁN (12 AM - 6 AM) ---
        hora_actual = datetime.datetime.now().hour
        es_noche_critica = (hora_actual >= 0 and hora_actual < 6)
        
        # Sumar sospecha si hay alguien
        suspicion_levels[canal] = suspicion_levels.get(canal, 0) + 1
        
        # En la noche, la primera detección en el Yaris ya es Merodeo/Alerta
        es_merodeo = (suspicion_levels[canal] >= UMBRAL_MERODEO) or (es_yaris and es_noche_critica)

        # --- PASO 1: NOTIFICACIÓN INSTANTÁNEA (DIFERENCIADA) ---
        ja_notificado = notified_sessions.get(canal, False)
        es_canal_yaris = canal in [1, 2]
        
        if FIREBASE_READY and (es_merodeo or es_noche_critica) and not ja_notificado:
            if es_canal_yaris:
                titulo_alerta = f"🚨 TITÁN: ALERTA CRÍTICA CAM {canal}"
                body_alerta = "¡PERSONA DETECTADA cerca del Yaris!"
            else:
                titulo_alerta = f"🔍 TITÁN: VIGILANCIA SILENCIOSA CAM {canal}"
                body_alerta = "Movimiento detectado en zona perimetral."
            
            msg = messaging.Message(
                topic="yaris_alerts_9612765041", 
                notification=messaging.Notification(title=titulo_alerta, body=body_alerta),
                android=messaging.AndroidConfig(
                    priority='high',
                    ttl=datetime.timedelta(seconds=30)
                )
            )
            threading.Thread(target=messaging.send, args=(msg,), daemon=True).start()
            notified_sessions[canal] = True # BLOQUEAR MÁS AVISOS HASTA QUE SE VAYA
            logging.info(f"📢 PASO 1 OK: Notificación enviada a NeoMessage (Cam {canal}).")

        # --- PASO 2: REGISTRO Y EVIDENCIA (SEGUNDO PLANO) ---
        evento = {
            "c": canal,
            "t": int(time.time()),
            "msg": "SOSPECHA DE MERODEO" if es_merodeo else "TRANSEÚNTE DETECTADO",
            "p": "9612765041"
        }
        respaldo_json_seguro(evento)
        
        # --- FILTRO DE SATURACIÓN PARA NOTIFICACIONES ---
        ahora = time.time()
        ultimo = last_alert_times.get(canal, 0)
        
        if es_yaris and es_noche_critica:
            cooldown = 5
        elif es_merodeo:
            cooldown = 30
        else:
            cooldown = 120
            
        if ahora - ultimo < cooldown:
            return 
            
        last_alert_times[canal] = ahora
        if es_merodeo: suspicion_levels[canal] = 0

        # Generar Video y Subir (Mismo flujo v7.8)
        if not os.path.exists("grabaciones"): os.makedirs("grabaciones")
        path = f"grabaciones/alert_{canal}_{int(time.time())}.avi"
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(path, fourcc, 10.0, (640, 480))
        for f in buffer_video: out.write(cv2.resize(f, (640, 480)))
        out.release()

        # --- AUTENTICACIÓN Y SUBIDA AL SERVIDOR ---
        logging.info(f"⏳ PASO 2: Sincronizando con Servidor (.144)...")
        es_canal_yaris = canal in [1, 2]
        tipo_pb = "CRÍTICA" if es_canal_yaris else "SILENCIOSA"
        
        try:
            # Login rápido para obtener permiso
            r_auth = requests.post(f"http://192.168.100.144:8090/api/admins/auth-with-password", 
                                  json={"identity": PB_USER, "password": PB_PASS}, timeout=5)
            
            if r_auth.status_code != 200:
                logging.error(f"❌ ERROR DE LOGIN: {r_auth.text}")
                return # Si no hay login, no podemos subir nada
                
            token = r_auth.json().get("token", "")
            headers = {"Authorization": token}

            # Subir Alerta
            r1 = requests.post(f"{BASE_PB}/alertas_yaris/records", 
                         json={"titulo": f"🚨 TITÁN: ALERTA {tipo_pb} CAM {canal}", "mensaje": "Persona Detectada"}, 
                         headers=headers, timeout=5)
            
            # Subir Video
            with open(path, 'rb') as f_vid:
                r2 = requests.post(f"{BASE_PB}/videos_yaris/records", 
                             data={"descripcion": f"Cam {canal} ({tipo_pb})"}, 
                             files={'archivo': (path, f_vid, 'video/avi')}, 
                             headers=headers, timeout=20)
            
            logging.info(f"✅ SERVIDOR SINCRONIZADO (Status: {r1.status_code}, {r2.status_code})")
        except Exception as e:
            logging.error(f"❌ FALLO CRÍTICO EN SERVIDOR: {e}")
        
        logging.info(f"✅ ALERTA ENVIADA A NEOMESSAGE (Cam {canal})")
    except Exception as e:
        logging.error(f"⚠️ Error en procesamiento de alerta: {e}")

# -------------------------------------------------
# CAPTURA Y MAIN (Vínculo Directo NeoMessage)
# -------------------------------------------------
class TitanCam:
    def __init__(self, canal):
        self.canal = canal
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
        self.url = f"rtsp://{CAM_USER}:{CAM_PASS}@{IP_CAMS}:554/user={CAM_USER}&password={CAM_PASS}&channel={canal}&stream=1.sdp"
        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.frame = None
        self.buffer = []
        threading.Thread(target=self._update, daemon=True).start()

    def _update(self):
        while True:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
                self.buffer.append(frame)
                if len(self.buffer) > BUFFER_SIZE: self.buffer.pop(0)
            else:
                self.cap.release()
                time.sleep(2)
                self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)

def main():
    logging.info("🚀 TITAN v8.0: INTELIGENCIA + AUTO-LIMPIEZA ACTIVADA")
    cv2.namedWindow("TITAN YARIS LIVE", cv2.WINDOW_NORMAL)
    cams = [TitanCam(i) for i in (1, 2, 3, 4)]
    subs = [cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=30) for _ in range(4)]
    last_alert = [0] * 4

    while True:
        frames = []
        for i, cam in enumerate(cams):
            if cam.frame is None:
                frames.append(np.zeros((240, 320, 3), np.uint8))
                continue
            f_small = cv2.resize(cam.frame, (320, 240))
            mask = subs[i].apply(f_small)
            motion = cv2.countNonZero(cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)[1])
            if motion > MOVEMENT_THRESHOLD and time.time() - last_alert[i] > COOLDOWN_SECONDS:
                last_alert[i] = time.time()
                threading.Thread(target=procesar_alerta_con_video, args=(cam.canal, list(cam.buffer)), daemon=True).start()
            frames.append(f_small)
        if len(frames) == 4:
            grid = np.vstack((np.hstack((frames[0], frames[1])), np.hstack((frames[2], frames[3]))))
            cv2.imshow("TITAN YARIS LIVE", grid)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cv2.destroyAllWindows()

if __name__ == "__main__": main()
