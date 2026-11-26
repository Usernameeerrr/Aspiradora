# Aspiradora robot · Código de la ESP32 y la Raspberry Pi

Estos archivos reconstruyen las pruebas de comunicación y control de movimiento.
Los nombres y las órdenes principales corresponden al trabajo documentado.
La temporización de parada, la consulta ESTADO y la validación de GPIO
son decisiones de esta versión. El protocolo de esta reconstrucción usa
texto ASCII con final de línea y 115200 baudios.

| Archivo | Función |
|---|---|
| `ESP32/PruebaESP32/PruebaESP32.ino` | Prueba que la placa envía texto al puerto serial. |
| `ESP32/ControlMovimiento/ControlMovimiento.ino` | Recibe órdenes y controla dos salidas del puente H L298N con PWM. |
| `ESP32/ControlMovimiento/pines_l298n.h` | Guarda los seis GPIO y el sentido de giro de cada rueda. |
| `Raspberry/control_esp32.py` | Consulta el estado del firmware por USB. |
| `Raspberry/control_movimiento.py` | Menú para probar avance, retroceso, giros, parada y velocidad. |

Los sketches se abren por separado en Arduino IDE. Usa la placa **ESP32 Dev
Module** con el núcleo **Arduino-ESP32 3.x**. Para los archivos Python de la Raspberry
se requiere **pyserial**. Ambos reciben la opción `--puerto` con el dispositivo USB
identificado como la ESP32. Abre el enlace serial desde un solo programa a la vez.

Los GPIO de `pines_l298n.h` están en `-1` hasta que se indiquen los del montaje,
por lo que el firmware deja el control deshabilitado al cargarlo tal como está.
Con los GPIO configurados, el menú envía pulsos cortos de movimiento.
El firmware se detiene si pasan 650 ms sin recibir una orden de movimiento.
El carácter `S` seguido de un final de línea también solicita la parada.

La reconstrucción está pendiente de una prueba física con la ESP32 y el puente H.
Para el entregable E1, presenta estos archivos como **código reconstruido**.
Los originales recuperados de cámara y planificación siguen disponibles en
[Codigos_Aspiradora_Camara_LiDAR_Raspberry.zip](https://chatgpt.com/library?file_id=libfile_292a156eadec81919195f932058b985c&account_id=personal).

[Referencia de la API PWM LEDC de Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html)
