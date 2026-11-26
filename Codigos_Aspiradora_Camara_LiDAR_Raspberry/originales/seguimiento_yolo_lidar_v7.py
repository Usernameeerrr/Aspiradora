import json
import math
import os
import queue
import threading
import time
from pathlib import Path

import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

# ASPIRADORA ROBOT: V7 YOLO + LIDAR (SOLO DIAGNOSTICO)
BASE = Path.home() / 'AspiradoraRobot'
MODELO = BASE / 'YOLO/Modelos/Domestico_V2_480/best480_ncnn_model'
LIDAR_JSON = BASE / 'Integracion/estado_lidar.json'
ANCHO, ALTO = 640, 480
ROI = (80, 60, 560, 420)
CONFIANZA = 0.25
MAX_EDAD_LIDAR = 2.0
MAX_EDAD_YOLO = 1.0
NOMBRES = {'cap': 'TAPA', 'paper': 'PAPEL', 'plastic': 'PLASTICO', 'shell': 'CASCARA'}
ZONAS = ('FRENTE', 'FRENTE_IZQUIERDO', 'FRENTE_DERECHO', 'IZQUIERDA', 'DERECHA')

cola = queue.Queue(maxsize=1)
parar = threading.Event()
candado = threading.Lock()
estado = {'tiempo': 0.0, 'cajas': [], 'objetivo': None, 'ms': 0.0}
fallo = {'texto': None}


def direccion(x):
    if x < ANCHO * 0.35:
        return 'IZQUIERDA'
    if x > ANCHO * 0.65:
        return 'DERECHA'
    return 'CENTRO'


def procesar_yolo():
    try:
        modelo = YOLO(str(MODELO), task='detect')
        anteriores = []
        while not parar.is_set():
            try:
                fotograma = cola.get(timeout=0.2)
            except queue.Empty:
                continue
            x1, y1, x2, y2 = ROI
            inicio = time.perf_counter()
            pred = modelo.predict(
                source=fotograma[y1:y2, x1:x2],
                imgsz=480,
                conf=CONFIANZA,
                device='cpu',
                verbose=False,
            )[0]
            nuevas = []
            usados = set()
            for caja in pred.boxes:
                clase = int(caja.cls[0].item())
                etiqueta = str(pred.names[clase])
                confianza = float(caja.conf[0].item())
                a, b, c, d = [float(v) for v in caja.xyxy[0].tolist()]
                a, b, c, d = a+x1, b+y1, c+x1, d+y1
                cx, cy = (a+c)/2, (b+d)/2
                coincidencia = None
                for idx, previa in enumerate(anteriores):
                    if idx in usados or previa['clase'] != clase:
                        continue
                    if math.hypot(cx-previa['cx'], cy-previa['cy']) < 80:
                        coincidencia = idx
                        break
                confirmado = 1
                if coincidencia is not None:
                    usados.add(coincidencia)
                    confirmado = anteriores[coincidencia]['veces'] + 1
                nuevas.append({
                    'clase': clase, 'etiqueta': NOMBRES.get(etiqueta, etiqueta.upper()),
                    'conf': confianza, 'caja': (int(a), int(b), int(c), int(d)),
                    'cx': cx, 'cy': cy, 'veces': confirmado,
                })
            anteriores = nuevas
            confirmadas = [d for d in nuevas if d['veces'] >= 2]
            objetivo = max(confirmadas, key=lambda d: d['conf'], default=None)
            with candado:
                estado.update(
                    tiempo=time.time(), cajas=nuevas, objetivo=objetivo,
                    ms=(time.perf_counter()-inicio)*1000,
                )
    except Exception as exc:
        fallo['texto'] = str(exc)
        parar.set()


def leer_lidar():
    try:
        datos = json.loads(LIDAR_JSON.read_text(encoding='utf-8'))
        edad = time.time() - float(datos.get('timestamp', 0))
        if not 0 <= edad <= MAX_EDAD_LIDAR:
            return None, 'DATOS ANTIGUOS'
        if datos.get('sensor') != 'YDLIDAR_X2L':
            return None, 'SENSOR NO IDENTIFICADO'
        return datos, f'ACTIVO ({edad:.1f} s)'
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None, 'SIN DATOS'


def poner(img, texto, y, color=(230, 230, 230), escala=0.49):
    cv2.putText(img, texto, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                escala, color, 1, cv2.LINE_AA)


def iniciar():
    if not MODELO.exists():
        raise FileNotFoundError(f'No existe el modelo: {MODELO}')
    camara = Picamera2()
    configuracion = camara.create_video_configuration(
        main={'size': (ANCHO, ALTO), 'format': 'RGB888'},
        controls={'AeEnable': True, 'AwbEnable': True,
                  'FrameDurationLimits': (66666, 66666)},
    )
    camara.configure(configuracion)
    camara.start()
    hilo = threading.Thread(target=procesar_yolo, daemon=True)
    hilo.start()
    cv2.namedWindow('ASPIRADORA V7 - YOLO + LIDAR', cv2.WINDOW_NORMAL)
    try:
        while not parar.is_set():
            cuadro = camara.capture_array()
            try:
                if cola.full():
                    cola.get_nowait()
                cola.put_nowait(cuadro.copy())
            except queue.Empty:
                pass
            except queue.Full:
                pass

            pantalla = cv2.copyMakeBorder(
                cuadro, 0, 270, 0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0)
            )
            x1, y1, x2, y2 = ROI
            cv2.rectangle(pantalla, (x1, y1), (x2, y2), (0, 255, 255), 2)
            with candado:
                datos_yolo = dict(estado)
            reciente = time.time()-datos_yolo['tiempo'] <= MAX_EDAD_YOLO
            objetivo = datos_yolo['objetivo'] if reciente else None
            if reciente:
                for d in datos_yolo['cajas']:
                    a, b, c, e = d['caja']
                    color = (0, 220, 0) if d['veces'] >= 2 else (0, 155, 255)
                    cv2.rectangle(pantalla, (a, b), (c, e), color, 2)
                    poner(pantalla, f"{d['etiqueta']} {d['conf']:.0%}",
                          max(20, b-6), color, 0.5)
            if objetivo:
                cx, cy = int(objetivo['cx']), int(objetivo['cy'])
                cv2.line(pantalla, (ANCHO//2, ALTO), (cx, cy), (0, 255, 0), 2)
                msg = f"OBJETIVO: {objetivo['etiqueta']} - {direccion(cx)}"
            else:
                msg = 'BUSCANDO RESIDUOS CONFIRMADOS'
            poner(pantalla, msg, 502, (255, 255, 255), 0.54)
            fps = 1000/datos_yolo['ms'] if reciente and datos_yolo['ms'] else 0.0
            poner(pantalla, f"YOLO: {datos_yolo['ms']:.0f} ms | {fps:.1f} FPS", 525)

            lidar, estado_lidar = leer_lidar()
            poner(pantalla, f'LIDAR: {estado_lidar}', 548,
                  (80, 220, 100) if lidar else (0, 165, 255))
            zonas = lidar.get('zonas', {}) if lidar else {}
            for idx, nombre in enumerate(ZONAS):
                z = zonas.get(nombre, {})
                e = z.get('estado', 'DESCONOCIDO')
                if e not in ('LIBRE', 'OBSTACULO', 'DESCONOCIDO'):
                    e = 'DESCONOCIDO'
                distancia = z.get('distancia_minima')
                distancia_txt = f'{distancia:.2f} m' if isinstance(distancia, (int,float)) else '--'
                color = ((50, 220, 80) if e == 'LIBRE' else
                         (30, 60, 255) if e == 'OBSTACULO' else (0, 190, 255))
                poner(pantalla, f'{nombre}: {e} | {distancia_txt}',
                      572 + idx*22, color)
            frente = [zonas.get(n, {}).get('estado', 'DESCONOCIDO')
                      for n in ZONAS[:3]]
            if not lidar:
                decision = 'NO AVANZAR: LIDAR SIN DATOS ACTUALES'
            elif 'OBSTACULO' in frente:
                decision = 'NO AVANZAR: OBSTACULO FRONTAL'
            elif any(e != 'LIBRE' for e in frente):
                decision = 'NO AVANZAR: FRENTE DESCONOCIDO'
            elif lidar.get('orientacion_verificada') is not True:
                decision = 'NO AVANZAR: ORIENTACION SIN CALIBRAR'
            else:
                decision = 'SOLO PRUEBA: MOVIMIENTO NO AUTORIZADO'
            poner(pantalla, decision, 698, (0, 190, 255), 0.46)
            poner(pantalla, 'MOTORES DESACTIVADOS | Q PARA SALIR', 725)
            cv2.imshow('ASPIRADORA V7 - YOLO + LIDAR', pantalla)
            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                break
        if fallo['texto']:
            print('ERROR EN YOLO:', fallo['texto'])
    finally:
        parar.set()
        hilo.join(timeout=3)
        camara.stop()
        camara.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    iniciar()
