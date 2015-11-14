#include <EEPROM.h>

#define STATE_INITIATING 0
#define STATE_STAND_BY 1
#define STATE_ACTIVE 2
#define STATE_PENDING_REFERENCE 3
#define STATE_CAPTURING_REFERENCE 4

#define PIN_LED A2
#define PIN_BUTTON A3
#define PIN_SWITCH 13
#define PIN_TRIG 2
#define PIN_ECHO 3
#define EEPROM_REF_VAL_ADDR 132

#define SWITCH_THRESHOLD_PERC 20
#define CAPTURING_DELAY_SEC 5
#define STAY_ACTIVE_SEC 3

const uint8_t valueUpdateDelay = 25;
const uint8_t displayValueDelay = 250;

int _currentState = STATE_INITIATING;
float _referenceValue = 0;

class IValueProvider
{
  public:
    virtual ~IValueProvider() {}
    virtual float GetValue() = 0;
};

class SonarReader : public IValueProvider
{
  private:
    uint8_t _trigPin = 0;
    uint8_t _echoPin = 0;
  public:
    SonarReader(uint8_t trigPin, uint8_t echoPin)
    {
      _trigPin = trigPin;
      _echoPin = echoPin;
      pinMode(_trigPin, OUTPUT);
      pinMode(_echoPin, INPUT);
    }
    virtual float GetValue()
    {
      uint32_t duration; // duration of the round trip
      uint32_t cm;        // distance of the obstacle

      // The sensor is triggered by a HIGH pulse of 10 or more microseconds.
      // Give a short LOW pulse beforehand to ensure a clean HIGH pulse:

      digitalWrite(_trigPin, LOW);
      delayMicroseconds(3);

      // Start trigger signal
      digitalWrite(_trigPin, HIGH);
      delayMicroseconds(10);
      digitalWrite(_trigPin, LOW);

      // Read the signal from the sensor: a HIGH pulse whose
      // duration is the time (in microseconds) from the sending
      // of the ping to the reception of its echo off of an object.
      duration = pulseIn(_echoPin, HIGH);

      // convert the time into a distance
      cm = (uint32_t)((duration << 4) + duration) / 1000.0; // cm = 17 * duration/1000
      return cm;
    }
};

class ValueFilter : public IValueProvider
{
  private:
    uint8_t _filterSteps = 0;
    IValueProvider * _valueProvider;
    bool _initiation = 1;
    float _avarage = 0;
    void updateValue()
    {
      if (_initiation == 1)
      {
        _avarage = _valueProvider->GetValue();
        _initiation = 0;
      }
      _avarage = (_avarage * ((float)(_filterSteps - 1)) + _valueProvider->GetValue()) / (float)_filterSteps;
    }
  public:
    ValueFilter(IValueProvider * valueProvider, uint8_t filterSteps)
    {
      _filterSteps = filterSteps;
      _valueProvider = valueProvider;
    }
    virtual float GetValue()
    {
      updateValue();
      return _avarage;
    }
    virtual void ForceUpdate()
    {
      updateValue();
    }
};

SonarReader *_sonar;
ValueFilter *_filter;

void setup() {
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_SWITCH, OUTPUT);

  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_SWITCH, LOW);

  Serial.begin(9600);
  _sonar = new SonarReader(PIN_TRIG, PIN_ECHO);
  _filter = new ValueFilter(_sonar, 5);
}

int loopSkip = 0;
void loop() {
  // put your main code here, to run repeatedly:


  if (loopSkip >= displayValueDelay / valueUpdateDelay) {
    loopSkip = 0;
    processState();

    Serial.print("State");
    Serial.print(_currentState);
    Serial.println();
    Serial.print("Ref Value");
    Serial.print(_referenceValue);
    Serial.println();
    Serial.print("Value");
    Serial.print((float)(_filter->GetValue()));
    Serial.println();
  }

  _filter->ForceUpdate();
  delay(valueUpdateDelay);
  loopSkip ++;
}

void processState() {
  switch (_currentState) {
    case STATE_INITIATING:
      _currentState = processInitState();
      break;
    case STATE_STAND_BY:
      _currentState = processStandByState();
      break;
    case STATE_ACTIVE:
      _currentState = processActiveState();
      break;
    case STATE_PENDING_REFERENCE:
      _currentState = processPendingReferenceState();
      break;
    case STATE_CAPTURING_REFERENCE:
      _currentState = processCaptureingReferenceState();
      break;
    default:
      _currentState = processInitState();
      break;
  }
}

int processInitState() {
  if (_referenceValue == 0) {
    _referenceValue = readFromEeprom();
  }

  return STATE_STAND_BY;
}

int processStandByState() {
  if (digitalRead(PIN_BUTTON) == LOW)
  {
    return STATE_PENDING_REFERENCE;
  }

  if (abs(1 - getMeasuredValue() / _referenceValue) * 100 > SWITCH_THRESHOLD_PERC) {
    return STATE_ACTIVE;
  } else {
    return STATE_STAND_BY;
  }
}


unsigned long lastActiveTime = 0;
int processActiveState() {
  if (digitalRead(PIN_BUTTON) == LOW)
  {
    return STATE_PENDING_REFERENCE;
  }

  bool isActive = abs(1 - getMeasuredValue() / _referenceValue) * 100 > SWITCH_THRESHOLD_PERC;

  if (isActive)
  {
    lastActiveTime = millis();
  }

  // add delay before switch off
  if (isActive || (millis() - lastActiveTime) / 1000 < STAY_ACTIVE_SEC) {
    digitalWrite(PIN_SWITCH, HIGH);
    return STATE_ACTIVE;
  } else {
    digitalWrite(PIN_SWITCH, LOW);
    return STATE_STAND_BY;
  }
}

unsigned long pendingStartTime = 0;
unsigned long ledSwitchTime = 0;
int ledState = LOW;
int processPendingReferenceState() {
  if (pendingStartTime == 0) {
    pendingStartTime = millis();
  }

  if (ledSwitchTime == 0) {
    ledSwitchTime = millis();
    ledState = HIGH;
  }

  if ((millis() - ledSwitchTime) / 1000 > 1)
  {
    ledSwitchTime = 1;
    if (ledState == LOW)
    {
      ledState = HIGH;
    } else {
      ledState = LOW;
    }
  }

  digitalWrite(PIN_LED, ledState);

  if ((millis() - pendingStartTime) / 1000 > CAPTURING_DELAY_SEC ) {
    digitalWrite(PIN_LED, LOW);
    pendingStartTime = 0;
    ledSwitchTime = 0;
    ledState = LOW;
    return STATE_CAPTURING_REFERENCE;
  } else {
    return STATE_PENDING_REFERENCE;
  }
}

unsigned long capturingStartTime = 0;
float capturingAvgValue = 0;
int avgCounter = 0;
int processCaptureingReferenceState() {
  if (capturingStartTime == 0) {
    capturingStartTime = millis();
  }

  digitalWrite(PIN_LED, HIGH);

  capturingAvgValue = (capturingAvgValue * avgCounter + getMeasuredValue()) / (avgCounter + 1);
  avgCounter++;

  if ((millis() - capturingStartTime) / 1000 > CAPTURING_DELAY_SEC ) {
    digitalWrite(PIN_LED, LOW);
    _referenceValue = capturingAvgValue;
    saveToEeprom(_referenceValue);
    capturingStartTime = 0;
    capturingAvgValue = 0;
    avgCounter = 0;
    digitalWrite(PIN_SWITCH, LOW);
    return STATE_STAND_BY;
  } else {
    return STATE_CAPTURING_REFERENCE;
  }
}

float getMeasuredValue() {
  return _filter->GetValue();
}

void saveToEeprom(float refValue)
{
  EEPROMWriteInt(EEPROM_REF_VAL_ADDR, (int)(refValue * 100));
}

float readFromEeprom()
{
  float result = (float)(EEPROMReadInt(EEPROM_REF_VAL_ADDR)) / (float)100;
  return result;
}

void EEPROMWriteInt(int p_address, int p_value)
{
  Serial.println("WARNING: EEPROM write");

  byte lowByte = ((p_value >> 0) & 0xFF);
  byte highByte = ((p_value >> 8) & 0xFF);

  EEPROM.write(p_address, lowByte);
  EEPROM.write(p_address + 1, highByte);
}

unsigned int EEPROMReadInt(int p_address)
{
  byte lowByte = EEPROM.read(p_address);
  byte highByte = EEPROM.read(p_address + 1);

  return ((lowByte << 0) & 0xFF) + ((highByte << 8) & 0xFF00);
}


