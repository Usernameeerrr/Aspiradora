// Reconstrucción de la prueba de comunicación USB de la ESP32.
#include <Arduino.h>

void setup() {
    Serial.begin(115200);
    Serial.println("ESP32 FUNCIONANDO");
}

void loop() {
    static unsigned long ultimoAviso = 0;
    if (millis() - ultimoAviso >= 1000) {
        ultimoAviso = millis();
        Serial.println("ESP32 FUNCIONANDO");
    }
}
