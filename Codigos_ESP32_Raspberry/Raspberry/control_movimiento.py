"""Menú de prueba para el sketch reconstruido ControlMovimiento.ino."""
import argparse
import time

import serial

from control_esp32 import abrir_serial, consultar, detener

DIRECCIONES = {
    "1": "AVANZAR",
    "2": "RETROCEDER",
    "3": "IZQUIERDA",
    "4": "DERECHA",
}


def pulso(dispositivo, direccion):
    limite = time.monotonic() + 0.50
    try:
        while time.monotonic() < limite:
            respuesta = consultar(dispositivo, direccion, ("OK ", "ERROR:"), espera=0.20)
            if respuesta != f"OK {direccion}":
                print(respuesta or "Sin confirmación de movimiento.")
                return
            time.sleep(0.15)
    finally:
        print(detener(dispositivo) or "Sin confirmación de parada.")


def menu(dispositivo):
    while True:
        print(
            "\n1. Avanzar  2. Retroceder  3. Izquierda  4. Derecha"
            "\n5. Detener  6. Velocidad  7. Salir"
        )
        opcion = input("Opción: ").strip()
        if opcion in DIRECCIONES:
            pulso(dispositivo, DIRECCIONES[opcion])
        elif opcion == "5":
            print(detener(dispositivo) or "Sin confirmación de parada.")
        elif opcion == "6":
            try:
                valor = int(input("Velocidad (0 a 100): "))
                if not 0 <= valor <= 100:
                    raise ValueError
            except ValueError:
                print("Escribe un número entero entre 0 y 100.")
                continue
            respuesta = consultar(
                dispositivo, f"VELOCIDAD:{valor}", ("VELOCIDAD CONFIGURADA:", "ERROR:")
            )
            print(respuesta or "Sin confirmación de velocidad.")
        elif opcion == "7":
            return
        else:
            print("Opción desconocida.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", required=True, help="Puerto identificado de la ESP32")
    args = parser.parse_args()

    try:
        with abrir_serial(args.puerto) as dispositivo:
            time.sleep(1)
            estado = consultar(
                dispositivo, "ESTADO", ("LISTO", "PINES SIN CONFIGURAR"), espera=1
            )
            if estado != "LISTO":
                raise SystemExit(estado or "Sin respuesta de ControlMovimiento.ino.")
            try:
                menu(dispositivo)
            except (KeyboardInterrupt, EOFError):
                print()
            finally:
                print(detener(dispositivo) or "Sin confirmación de parada.")
    except serial.SerialException as error:
        raise SystemExit(f"Error serial: {error}") from error


if __name__ == "__main__":
    main()
