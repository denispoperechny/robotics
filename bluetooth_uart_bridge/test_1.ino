void setup() {
    Serial.begin(115200); // Set the baud rate
    pinMode(2, OUTPUT); // Initialize the built-in LED pin
}

int ct = 1;

void loop() {
    Serial.print("Hello, UART _ " + String(ct) + "\n"); // Send your message
    ct++; // Increment the counter
    digitalWrite(2, HIGH); // Turn the LED on
    delay(500); // Wait for half a second
    digitalWrite(2, LOW); // Turn the LED off
    delay(500); // Wait for another half a second
}
