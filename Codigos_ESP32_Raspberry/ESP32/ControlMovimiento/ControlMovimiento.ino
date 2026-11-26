// Reconstrucción para ESP32 Dev Module con Arduino-ESP32 3.x.
#include <Arduino.h>
#include <stdlib.h>
#include <string.h>
#include "pines_l298n.h"

constexpr unsigned long TIEMPO_SIN_ORDEN_MS = 650;
constexpr uint32_t FRECUENCIA_PWM = 5000;
constexpr uint8_t BITS_PWM = 8;
constexpr int PINES[] = {PIN_ENA, PIN_IN1, PIN_IN2, PIN_ENB, PIN_IN3, PIN_IN4};

unsigned int velocidad = 45;
unsigned long ultimaOrden = 0;
bool habilitado = false;
bool moviendo = false;
int izquierdaActual = 0;
int derechaActual = 0;
char linea[40];
size_t longitud = 0;
bool descartarLinea = false;

bool pinesValidos() {
    // GPIO de salida de uso general para el ESP32 clásico.
    constexpr int SALIDAS[] = {4, 13, 14, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33};
    for (size_t i = 0; i < sizeof(PINES) / sizeof(PINES[0]); ++i) {
        bool permitido = false;
        for (int pin : SALIDAS) {
            permitido |= PINES[i] == pin;
        }
        if (!permitido) {
            return false;
        }
        for (size_t j = 0; j < i; ++j) {
            if (PINES[i] == PINES[j]) {
                return false;
            }
        }
    }
    return true;
}

void salidasEnBajo() {
    for (int pin : PINES) {
        digitalWrite(pin, LOW);
    }
}

void detener() {
    if (habilitado) {
        ledcWrite(PIN_ENA, 0);
        ledcWrite(PIN_ENB, 0);
        digitalWrite(PIN_IN1, LOW);
        digitalWrite(PIN_IN2, LOW);
        digitalWrite(PIN_IN3, LOW);
        digitalWrite(PIN_IN4, LOW);
    }
    izquierdaActual = 0;
    derechaActual = 0;
    moviendo = false;
}

void ponerDireccion(int pin1, int pin2, int direccion) {
    digitalWrite(pin1, direccion > 0 ? HIGH : LOW);
    digitalWrite(pin2, direccion < 0 ? HIGH : LOW);
}

void mover(int izquierda, int derecha) {
    if (izquierda != izquierdaActual || derecha != derechaActual) {
        detener();
        ponerDireccion(PIN_IN1, PIN_IN2, INVERTIR_IZQUIERDA ? -izquierda : izquierda);
        ponerDireccion(PIN_IN3, PIN_IN4, INVERTIR_DERECHA ? -derecha : derecha);
        izquierdaActual = izquierda;
        derechaActual = derecha;
    }
    const unsigned int pwm = velocidad * 255 / 100;
    ledcWrite(PIN_ENA, izquierda != 0 ? pwm : 0);
    ledcWrite(PIN_ENB, derecha != 0 ? pwm : 0);
    ultimaOrden = millis();
    moviendo = velocidad != 0;
}

void procesar(const char* orden) {
    if (strcmp(orden, "ESTADO") == 0) {
        Serial.println(habilitado ? "LISTO" : "PINES SIN CONFIGURAR O PWM NO DISPONIBLE");
        return;
    }
    if (strcmp(orden, "DETENER") == 0 || strcmp(orden, "S") == 0) {
        detener();
        Serial.println("AMBOS MOTORES DETENIDOS");
        return;
    }
    if (strncmp(orden, "VELOCIDAD:", 10) == 0) {
        const char* valor = orden + 10;
        char* fin = nullptr;
        long nueva = strtol(valor, &fin, 10);
        if (fin == valor || *fin != '\0' || nueva < 0 || nueva > 100) {
            detener();
            Serial.println("ERROR: USA UN VALOR ENTRE 0 Y 100");
            return;
        }
        detener();
        velocidad = static_cast<unsigned int>(nueva);
        Serial.print("VELOCIDAD CONFIGURADA: ");
        Serial.print(velocidad);
        Serial.println("%");
        return;
    }

    int izquierda = 0;
    int derecha = 0;
    if (strcmp(orden, "AVANZAR") == 0) {
        izquierda = 1;
        derecha = 1;
    } else if (strcmp(orden, "RETROCEDER") == 0) {
        izquierda = -1;
        derecha = -1;
    } else if (strcmp(orden, "IZQUIERDA") == 0) {
        izquierda = -1;
        derecha = 1;
    } else if (strcmp(orden, "DERECHA") == 0) {
        izquierda = 1;
        derecha = -1;
    } else {
        detener();
        Serial.println("ERROR: ORDEN NO RECONOCIDA");
        return;
    }
    if (!habilitado) {
        Serial.println("ERROR: CONTROL DESHABILITADO");
        return;
    }
    mover(izquierda, derecha);
    Serial.print("OK ");
    Serial.println(orden);
}

void setup() {
    Serial.begin(115200);
    if (pinesValidos()) {
        for (int pin : PINES) {
            pinMode(pin, OUTPUT);
        }
        salidasEnBajo();
        const bool pwmA = ledcAttach(PIN_ENA, FRECUENCIA_PWM, BITS_PWM);
        const bool pwmB = ledcAttach(PIN_ENB, FRECUENCIA_PWM, BITS_PWM);
        habilitado = pwmA && pwmB;
        if (!habilitado) {
            if (pwmA) {
                ledcDetach(PIN_ENA);
            }
            if (pwmB) {
                ledcDetach(PIN_ENB);
            }
            pinMode(PIN_ENA, OUTPUT);
            pinMode(PIN_ENB, OUTPUT);
            salidasEnBajo();
        }
    }
    Serial.println(habilitado ? "ESP32 ACTIVA - CONTROL DISPONIBLE"
                             : "ESP32 ACTIVA - CONTROL DESHABILITADO");
}

void loop() {
    if (moviendo && millis() - ultimaOrden >= TIEMPO_SIN_ORDEN_MS) {
        detener();
        Serial.println("DETENIDO: TIEMPO SIN ORDEN");
    }

    // Limita la lectura por vuelta para que el temporizador se siga revisando.
    for (int i = 0; i < 40 && Serial.available() > 0; ++i) {
        const char caracter = static_cast<char>(Serial.read());
        if (caracter == '\n' || caracter == '\r') {
            if (descartarLinea) {
                Serial.println("ERROR: LINEA DEMASIADO LARGA");
            } else if (longitud != 0) {
                linea[longitud] = '\0';
                procesar(linea);
            }
            longitud = 0;
            descartarLinea = false;
        } else if (!descartarLinea) {
            if (longitud < sizeof(linea) - 1) {
                linea[longitud++] = caracter;
            } else {
                detener();
                descartarLinea = true;
            }
        }
    }
}
