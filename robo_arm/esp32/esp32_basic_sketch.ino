
#include <ESP32Servo.h>
#include <Adafruit_MPU6050.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>

Adafruit_MPU6050 mpu;
Servo servo_a;
Servo servo_b;
Servo servo_c;

void setup(void) {
  Serial.begin(115200);
  while (!Serial)
    delay(10);

  if (!mpu.begin()) {
    Serial.println("MPU6050 not found.");
    while (1) {
      delay(100);
    }
  }

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);

  Serial.println("");
  delay(100);

  servo_a.attach(25); 
  servo_b.attach(26); 
  servo_c.attach(27); 
}

boolean set_arm_servo_a(int val) {
  //top
  // range: 25..180
  // 160 -> 0 (vertical)
  // 64 -> 90 (horizontal, forward)
 float a = -1.07;
 float b = 160;
 float calculated_servo_angle = (val * a + b);

  if (calculated_servo_angle < 25 || calculated_servo_angle > 180){
    return 0;
  }

  servo_a.write(calculated_servo_angle);
  return 1;
}

boolean set_arm_servo_b(int val) {
  //mid
  // range: 20...136
  // 44 -> 0 (vertical)
  // 136 -> 90 (horizontal, forward)
  float a = 1.02;
  float b = 44;
  float calculated_servo_angle = (val * a + b);

  if (calculated_servo_angle < 20 || calculated_servo_angle > 136){
    return 0;
  }

  servo_b.write(calculated_servo_angle);
  return 1;
}

boolean set_arm_servo_c(int val) {
  //base
  // range: 20...135
  // 84 -> 0 straight
  // 120 -> 33 left
  float a = 1.09;
  float b = 84;
  float calculated_servo_angle = (val * a + b);

  if (calculated_servo_angle < 20 || calculated_servo_angle > 135){
    return 0;
  }

  servo_c.write(calculated_servo_angle);
  return 1;
}

void parseStringToArray(String input_string, int* numbers, int max_size) {
  int currentIndex = 0;

  while (input_string.length() > 0 && currentIndex < max_size) {
    int delimiterPos = input_string.indexOf(';');
    if (delimiterPos == -1) {
      numbers[currentIndex] = input_string.toInt();
      break;
    } else {
      String numStr = input_string.substring(0, delimiterPos);
      numbers[currentIndex] = numStr.toInt();
      input_string = input_string.substring(delimiterPos + 1);
      currentIndex++;
    }
  }
}

void processInputMessage(String input){
  int numbers[3];
  parseStringToArray(input, numbers, 3);
  set_arm_servo_a(numbers[0]);
  set_arm_servo_b(numbers[1]);
  set_arm_servo_c(numbers[2]);
}

int read_acc_ct = 0;

void loop() {
  read_acc_ct += 1;
  
  if (read_acc_ct == 10){
    read_acc_ct = 0;
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    // m/s^2
    Serial.print(a.acceleration.x);
    Serial.print(";");
    Serial.print(a.acceleration.y);
    Serial.print(";");
    Serial.print(a.acceleration.z);
    Serial.print(";");

    // rps
    Serial.print(g.gyro.x);
    Serial.print(";");
    Serial.print(g.gyro.y);
    Serial.print(";");
    Serial.print(g.gyro.z);
    Serial.print(";");
    Serial.println("");
  }
  

  if (Serial.available()) {
    String receivedData = Serial.readStringUntil('\n');
    processInputMessage(receivedData);
  }

  delay(10);
}
