void setup() {
  pinMode(26, OUTPUT);
  pinMode(2, OUTPUT);

}

int ct = 0;
int frequency = 20; // Hz
float duty = .75;
void loop() {
  digitalWrite(26, HIGH);
  delay((1000 / frequency) * (duty));
  digitalWrite(26, LOW);
  delay((1000 / frequency) * (1 - duty));

  ct += 1;

  // 1 second control LED
  digitalWrite(2, LOW);
  int cycles_in_second = frequency;
  if (ct % cycles_in_second == 0)
  {
    digitalWrite(2, HIGH);
  }

}
