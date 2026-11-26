"""Diagnóstico de referencia. Reconstruido para este paquete; sin control de motores."""
import argparse
import json
import math
import time
from pathlib import Path

ZONAS = (
    ("FRENTE", -15, 15),
    ("FRENTE_IZQUIERDO", 15, 45),
    ("FRENTE_DERECHO", -45, -15),
    ("IZQUIERDA", 45, 105),
    ("DERECHA", -105, -45),
)


def resumir(puntos, frente, invertir, umbral):
    distancias = {nombre: [] for nombre, _, _ in ZONAS}
    for punto in puntos:
        if not math.isfinite(punto.angle) or not 0.15 <= punto.range <= 5.0:
            continue
        angulo = math.degrees(punto.angle)
        angulo = (-angulo if invertir else angulo) - frente
        angulo = (angulo + 180) % 360 - 180
        for nombre, minimo, maximo in ZONAS:
            if minimo <= angulo < maximo:
                distancias[nombre].append(punto.range)
                break

    zonas = {}
    for nombre, valores in distancias.items():
        distancia = min(valores, default=None)
        if distancia is None:
            estado = "DESCONOCIDO"
        elif distancia <= umbral:
            estado = "OBSTACULO"
        else:
            estado = "LIBRE"
        zonas[nombre] = {"estado": estado, "distancia_minima": distancia}
    return zonas


def publicar(ruta, zonas):
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps({
        "sensor": "YDLIDAR_X2L",
        "timestamp": time.time(),
        "orientacion_verificada": False,
        "zonas": zonas,
    }), encoding="utf-8")
    temporal.replace(ruta)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", required=True)
    parser.add_argument("--frente-grados", type=float, default=0.0)
    parser.add_argument("--invertir", action="store_true")
    parser.add_argument("--umbral", type=float, default=0.35)
    parser.add_argument("--publicar", type=Path, help="Ruta opcional al JSON que lee V7")
    args = parser.parse_args()
    if not 0.15 <= args.umbral <= 5.0 or not math.isfinite(args.frente_grados):
        parser.error("Usa un umbral entre 0.15 y 5.0 m y un ángulo finito")

    import ydlidar

    if args.publicar:
        args.publicar.parent.mkdir(parents=True, exist_ok=True)
    ydlidar.os_init()
    lidar = ydlidar.CYdLidar()
    opciones = {
        ydlidar.LidarPropSerialPort: args.puerto,
        ydlidar.LidarPropSerialBaudrate: 115200,
        ydlidar.LidarPropDeviceType: ydlidar.YDLIDAR_TYPE_SERIAL,
        ydlidar.LidarPropLidarType: ydlidar.TYPE_TRIANGLE,
        ydlidar.LidarPropSingleChannel: True,
        ydlidar.LidarPropSampleRate: 3,
        ydlidar.LidarPropMinRange: 0.15,
        ydlidar.LidarPropMaxRange: 5.0,
    }
    for propiedad, valor in opciones.items():
        lidar.setlidaropt(propiedad, valor)

    activo = False
    try:
        if not lidar.initialize():
            raise SystemExit(f"No se pudo inicializar el LiDAR en {args.puerto}")
        activo = lidar.turnOn()
        if not activo:
            raise SystemExit("No se pudo iniciar el escaneo")
        scan = ydlidar.LaserScan()
        proximo_reporte = 0.0
        while ydlidar.os_isOk():
            if not lidar.doProcessSimple(scan):
                time.sleep(0.05)
                continue
            zonas = resumir(scan.points, args.frente_grados, args.invertir, args.umbral)
            ahora = time.monotonic()
            if ahora < proximo_reporte:
                continue
            proximo_reporte = ahora + 0.5
            if args.publicar:
                publicar(args.publicar, zonas)
            for nombre, valor in zonas.items():
                metros = valor["distancia_minima"]
                medida = "--" if metros is None else f"{metros:.3f} m"
                print(f"{nombre:19} {valor['estado']:11} {medida}")
            print()
    except KeyboardInterrupt:
        pass
    finally:
        if activo:
            lidar.turnOff()
        lidar.disconnecting()


if __name__ == "__main__":
    main()
