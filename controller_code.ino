#define LED1_PIN 10   // First LED
#define LED2_PIN 9    // Second LED
#define BUTTON_PIN 2  // Push button input

int mode = 1;  
int flash_rate = 1;
int flash_duration = 1;
int flash_pattern = 1;  
bool flashing = false;
bool button_was_pressed = false;
bool trigger_enabled = false;  
bool trigger_consumed = false; 
unsigned long last_press_time = 0;

void setup() {
  Serial.begin(9600);
  pinMode(LED1_PIN, OUTPUT);
  pinMode(LED2_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP); 
  digitalWrite(LED1_PIN, LOW);
  digitalWrite(LED2_PIN, LOW);
  Serial.println("Arduino Ready - Waiting for Configuration...");
}

void loop() {
  unsigned long current_time = millis();  

  if (mode == 2 && trigger_enabled && !trigger_consumed && digitalRead(BUTTON_PIN) == LOW) {
    if (!button_was_pressed && (current_time - last_press_time > 200)) {  
      Serial.println("BUTTON PRESSED - TRIGGERING LED");
      flashing = true;
      trigger_consumed = true;  
      button_was_pressed = true;
      last_press_time = current_time;
    }
  } else {
    button_was_pressed = false;
  }

  if (Serial.available()) {
    String command = Serial.readStringUntil('\n'); 
    Serial.print("Received: ");
    Serial.println(command);

    if (command.startsWith("SET")) {
      int temp_mode, temp_flash_rate, temp_duration, temp_pattern;
      int parsed = sscanf(command.c_str(), "SET %d %d %d %d", &temp_mode, &temp_flash_rate, &temp_duration, &temp_pattern);

      if (parsed == 4) {  
        mode = temp_mode;
        flash_rate = temp_flash_rate;
        flash_duration = temp_duration;
        flash_pattern = temp_pattern;
        trigger_enabled = (mode == 2);  
        trigger_consumed = false;  

        Serial.print("Mode: ");
        Serial.println(mode);
        Serial.print("Flash Rate: ");
        Serial.println(flash_rate);
        Serial.print("Duration: ");
        Serial.println(flash_duration);
        Serial.print("Pattern: ");
        Serial.println(flash_pattern);

        if (mode == 1) {
          flashing = true;  
          Serial.println("Manual Mode: Flashing started");
        } else {
          Serial.println("Trigger Mode: Waiting for button press...");
        }
      } else {
        Serial.println("Error parsing command!");
      }
    }
  }

  if (!flashing) {
    digitalWrite(LED1_PIN, LOW);
    digitalWrite(LED2_PIN, LOW);
  }

  if (flashing) {
    unsigned long start_time = millis();
    int delay_time = 1000 / (flash_rate * 2);

    // **Summary message before flashing begins**
    Serial.print("Flashing Pattern ");
    Serial.print(flash_pattern);
    Serial.print(" at ");
    Serial.print(flash_rate);
    Serial.print(" Hz for ");
    Serial.print(flash_duration);
    Serial.println(" seconds.");

    while (millis() - start_time < (flash_duration * 1000)) {
      if (flash_pattern == 1) {  
        digitalWrite(LED1_PIN, HIGH);
        delay(delay_time);
        digitalWrite(LED1_PIN, LOW);
        delay(delay_time);

      } else if (flash_pattern == 2) {  
        digitalWrite(LED1_PIN, HIGH);
        digitalWrite(LED2_PIN, LOW);
        delay(delay_time);

        digitalWrite(LED1_PIN, LOW);
        digitalWrite(LED2_PIN, HIGH);
        delay(delay_time);

      } else if (flash_pattern == 3) {  
        for (int i = 0; i < 2; i++) {  
          digitalWrite(LED1_PIN, HIGH);
          delay(delay_time);
          digitalWrite(LED1_PIN, LOW);
          delay(delay_time);
        }
        digitalWrite(LED2_PIN, HIGH);
        delay(delay_time);
        digitalWrite(LED2_PIN, LOW);
        delay(delay_time);

      } else if (flash_pattern == 4) {  
        for (int i = 0; i < 3; i++) {  
          digitalWrite(LED1_PIN, HIGH);
          delay(delay_time);
          digitalWrite(LED1_PIN, LOW);
          delay(delay_time);
        }
        digitalWrite(LED2_PIN, HIGH);
        delay(delay_time);
        digitalWrite(LED2_PIN, LOW);
        delay(delay_time);
      }
    }

    digitalWrite(LED1_PIN, LOW);
    digitalWrite(LED2_PIN, LOW);
    flashing = false;
    Serial.println("Flashing finished");
    Serial.println("DONE");
  }
}
