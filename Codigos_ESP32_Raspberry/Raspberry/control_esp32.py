"""Comunicación de referencia entre la Raspberry Pi y la ESP32 por USB."""
import argparse
import time

import serial


def abrir_serial(puerto):
    dispositivo = serial.Serial(
        port=None, baudrate=115200, timeout=0.05, write_timeout=0.25
    )
    dispositivo.dtr = False
    dispositivo.rts = False
    dispositivo.port = puerto
    dispositivo.open()
    return dispositivo


def consultar(dispositivo, orden, prefijos, espera=0.40):
    dispositivo.write((orden + "\n").encode("ascii"))
    limite = time.monotonic() + espera
    while time.monotonic() < limite:
        respuesta = dispositivo.read_until(b"\n", size=128)
        if not respuesta.endswith(b"\n"):
            continue
        texto = respuesta.decode("utf-8", errors="replace").strip()
        if texto.startswith(prefijos):
            return texto
    return ""


def detener(dispositivo):
    return consultar(dispositivo, "DETENER", ("AMBOS MOTORES DETENIDOS",))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", required=True, help="Puerto identificado de la ESP32")
    args = parser.parse_args()

    try:
        with abrir_serial(args.puerto) as dispositivo:
            time.sleep(1)
            respuesta = consultar(
                dispositivo, "ESTADO", ("LISTO", "PINES SIN CONFIGURAR"), espera=1
            )
            print(respuesta or "La ESP32 no respondió al protocolo de esta versión.")
    except serial.SerialException as error:
        raise SystemExit(f"Error serial: {error}") from error


if __name__ == "__main__":
    main()
