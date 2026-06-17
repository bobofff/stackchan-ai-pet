#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <M5Unified.h>
#include <WiFi.h>
#include <ESP32Servo.h>

#include "secrets.h"

Servo yawServo;
Servo pitchServo;

const int YAW_PIN = 1;
const int PITCH_PIN = 2;
const int YAW_CENTER = 90;
const int PITCH_CENTER = 90;

void drawFace(const char* expression, const char* line) {
  M5.Display.fillScreen(BLACK);
  M5.Display.setTextColor(WHITE);
  M5.Display.setTextSize(2);
  M5.Display.setCursor(12, 12);
  M5.Display.printf("%s\n", expression);
  M5.Display.setCursor(12, 58);
  M5.Display.printf("%s", line);
}

void centerHead() {
  yawServo.write(YAW_CENTER);
  pitchServo.write(PITCH_CENTER);
}

void playMotion(const char* motion) {
  if (strcmp(motion, "nod") == 0) {
    pitchServo.write(PITCH_CENTER + 18);
    delay(250);
    pitchServo.write(PITCH_CENTER - 12);
    delay(250);
  } else if (strcmp(motion, "shake") == 0) {
    yawServo.write(YAW_CENTER - 18);
    delay(220);
    yawServo.write(YAW_CENTER + 18);
    delay(220);
  } else if (strcmp(motion, "look_left") == 0) {
    yawServo.write(YAW_CENTER - 25);
    delay(500);
  } else if (strcmp(motion, "look_right") == 0) {
    yawServo.write(YAW_CENTER + 25);
    delay(500);
  } else if (strcmp(motion, "look_up") == 0) {
    pitchServo.write(PITCH_CENTER - 20);
    delay(500);
  } else if (strcmp(motion, "bounce") == 0) {
    pitchServo.write(PITCH_CENTER + 12);
    delay(150);
    pitchServo.write(PITCH_CENTER - 8);
    delay(150);
  }
  centerHead();
}

String requestTurn(const String& text) {
  HTTPClient http;
  http.begin(BRAIN_URL);
  http.addHeader("Content-Type", "application/json");
  if (strlen(DEVICE_SHARED_SECRET) > 0) {
    http.addHeader("X-Device-Secret", DEVICE_SHARED_SECRET);
  }

  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["user_text"] = text;
  doc["context"]["wake_reason"] = "button";
  doc["context"]["touch"] = M5.BtnA.isPressed() ? "button_a" : "";
  doc["context"]["battery_percent"] = M5.Power.getBatteryLevel();

  String body;
  serializeJson(doc, body);

  int status = http.POST(body);
  if (status <= 0) {
    http.end();
    return "";
  }
  String response = http.getString();
  http.end();
  return response;
}

void handleBrainResponse(const String& response) {
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, response);
  if (error) {
    drawFace("sad", "bad json");
    return;
  }

  const char* say = doc["say"] | "...";
  const char* expression = doc["expression"] | "neutral";
  const char* motion = doc["motion"] | "idle";

  drawFace(expression, say);
  playMotion(motion);

  // Hook TTS playback here. For v1, let the brain server return text only.
  // Later options: server-generated audio URL, I2S streaming, or local TTS.
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  drawFace("thinking", "wifi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
  }
  drawFace("happy", WiFi.localIP().toString().c_str());
}

void setup() {
  auto cfg = M5.config();
  M5.begin(cfg);
  Serial.begin(115200);

  yawServo.attach(YAW_PIN);
  pitchServo.attach(PITCH_PIN);
  centerHead();

  connectWifi();
  delay(1000);
  drawFace("neutral", "ready");
}

void loop() {
  M5.update();
  if (M5.BtnA.wasPressed()) {
    drawFace("thinking", "listening");
    String response = requestTurn("我按了一下你的按钮，跟我打个招呼。");
    if (response.length() == 0) {
      drawFace("sad", "brain offline");
    } else {
      handleBrainResponse(response);
    }
  }
  delay(20);
}

