# Aspiradora Robot · Códigos de cámara, LiDAR y Raspberry Pi

Paquete de referencia para el entregable E1. Los dos scripts de la carpeta
`originales` corresponden a las copias recuperadas de los programas del proyecto.
La carpeta `referencias` contiene un diagnóstico reconstruido para documentar y
repetir una prueba. Su contenido no acredita que ese archivo haya sido usado en
las pruebas anteriores.

| Archivo | Función | Procedencia |
|---|---|---|
| `originales/seguimiento_yolo_lidar_v7.py` | Configuración de Picamera2, detección de residuos con YOLO NCNN y lectura del estado del LiDAR | Código recuperado |
| `originales/planificador_rutas.py` | Planificación BFS, UCS, Greedy y A* sobre un mapa de ocupación | Código recuperado |
| `referencias/diagnostico_x2l.py` | Lectura del X2L, distancias por sector y publicación opcional del JSON que lee V7 | Reconstrucción, pendiente de prueba en Raspberry |

## Cámara y visión en la Raspberry Pi

El módulo del proyecto es la OV5647. La versión V7 configura Picamera2 con
resolución de 640 × 480, formato RGB888, exposición y balance de blancos
automáticos. Procesa la región de interés (80, 60, 560, 420), usa un umbral de
confianza de 0.25 y trabaja con las clases tapa, papel, plástico y cáscara.

El código V7 usa Picamera2, OpenCV y Ultralytics. Busca el modelo en:

```text
~/AspiradoraRobot/YOLO/Modelos/Domestico_V2_480/best480_ncnn_model
```

Con el modelo y las dependencias disponibles, desde la carpeta extraída:

```bash
source ~/AspiradoraRobot/yolo_env/bin/activate
python originales/seguimiento_yolo_lidar_v7.py
```

Pulsa Q para cerrar la ventana. V7 es un programa de diagnóstico y mantiene los
motores desactivados. Sin un productor de datos del LiDAR, muestra el estado
correspondiente a datos ausentes o antiguos.

## LiDAR YDLIDAR X2L

Se usó el entorno `~/lidar_env`, la biblioteca Python `ydlidar` y una
velocidad serial de 115200. En pruebas con ambos dispositivos conectados,
el LiDAR apareció como `/dev/ttyUSB1` y la ESP32 como `/dev/ttyUSB0`.
En pruebas con la ESP32 desconectada, el LiDAR llegó a aparecer como
`/dev/ttyUSB0`. Esas asignaciones son resultados de las pruebas.

Para consultar los adaptadores conectados en la Raspberry:

```bash
lsusb
ls -l /dev/serial/by-id/ /dev/ttyUSB* 2>/dev/null
```

Si ya está identificado el puerto del LiDAR, puedes introducirlo en el
diagnóstico reconstruido. Déjalo fijo y coloca una caja a una distancia conocida
en el frente físico. Compara la distancia reportada y luego revisa qué sector
aparece al mover la caja hacia cada lado. El umbral y los sectores de este
diagnóstico son valores de referencia. Los ajustes de frente e inversión
requieren comprobación en el montaje.

```bash
read -r -p 'Puerto del LiDAR identificado: ' puerto
~/lidar_env/bin/python referencias/diagnostico_x2l.py --puerto "$puerto"
```

Para alimentar la pantalla de V7, ejecuta el diagnóstico con esta opción:

```bash
~/lidar_env/bin/python referencias/diagnostico_x2l.py --puerto "$puerto" \
  --publicar "$HOME/AspiradoraRobot/Integracion/estado_lidar.json"
```

Este diagnóstico mantiene `orientacion_verificada` en falso. El estado
`LIBRE` solo describe los retornos observados en un sector y no controla el robot.
Detén el diagnóstico con Ctrl+C.

Referencia de configuración del X2L: [documentación del SDK de YDLIDAR](https://github.com/YDLIDAR/YDLidar-SDK/blob/master/doc/YDLIDAR_SDK_API_for_Developers.md).

## Comprobación de la Raspberry Pi

```bash
cat /etc/os-release
uname -m
python3 --version
~/lidar_env/bin/python -c 'import ydlidar; print("YDLIDAR disponible")'
~/AspiradoraRobot/yolo_env/bin/python -c 'import cv2, picamera2, ultralytics; print("Vision disponible")'
```

## Planificación en Raspberry Pi

El planificador incluye una demostración que funciona en Python sin cámara ni
LiDAR conectado:

```bash
python3 originales/planificador_rutas.py --demo
```

Prueba histórica sobre el mapa real, desde (193, 109) hasta (77, 206).
El CSV y el JSON se generaron en la Raspberry.

| Algoritmo | Pasos | Celdas exploradas | Tiempo |
|---|---:|---:|---:|
| BFS | 213 | 2823 | 30.919 ms |
| UCS | 213 | 2823 | 41.910 ms |
| Greedy | 225 | 270 | 4.827 ms |
| A* | 213 | 2254 | 26.795 ms |

Si conservas el mapa de la prueba en la Raspberry, este comando reproduce la
comparación con las mismas celdas. Los tiempos varían entre ejecuciones.

```bash
python3 originales/planificador_rutas.py \
  --mapa "$HOME/AspiradoraRobot/Mapas/ocupacion_v2_20261020_161217.csv" \
  --libre 0.018 --inicio 193 109 --meta 77 206 --algoritmo TODOS
```

## Archivos identificados en pruebas previas

Las pruebas también hacen referencia a `calibrar_camara.py`,
`calibracion_tiempo_real.py`, `diagnostico_lidar.py`,
`diagnostico_lidar_usb0.py`, `deteccion_obstaculos_usb0.py`,
`mapa_ocupacion.py`, `SLAM/slam_manual_v4.py` y
`control_movimiento.py`. Sus copias completas no se recuperaron para este
paquete. Los pesos de YOLO, los datos de entrenamiento, los mapas y el firmware
de la ESP32 se conservan como evidencias aparte si están disponibles.
