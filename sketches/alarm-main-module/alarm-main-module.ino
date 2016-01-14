
// TODO: RENAME STATES IDS DEFINITIONS
// TODO: Add interruptions?


#define DEBUG false

#define RESET_PIN_PEREPHERIALS 2 // writes
#define DISABLE_PIN 3 // reads
#define IS_ACTIVE_STATUS_PIN 4 // writes

#define SENSOR_PIN_1 5 // reads
#define SENSOR_PIN_2 6 // reads
#define SENSOR_PIN_3 7 // reads
#define SENSOR_PIN_4 8 // reads

#define ALARM_PIN 9 // writes

#define RED_LIGHT_PIN 12 // writes
#define YELLOW_LIGHT_PIN 10 // writes
#define GREEN_LIGHT_PIN 11 // writes

#define initializationId 1
#define activatedId 2
#define deactivatedId 3
#define alarmId 4

#define alarmActiveSeconds 30
#define resetDelayMillis 1000
#define loopDelay 25


class SafeInputReader
{
private:
  int _pinToRead = 0;
  int _signalValue = HIGH;
  bool _interruptCaught = false;

  void switched() 
  {
    _interruptCaught = true;
  }
public:
  SafeInputReader(int pinToRead)//, int signalValue)
  {
    _signalValue = HIGH;
    _pinToRead = pinToRead;
    //_signalValue = signalValue;
  }

  bool IsInputSwitched()
  {
    int readResult = digitalRead(_pinToRead);
    //bool interruptCaught = _catchedInterruptions[_pinToRead];
    bool result = readResult == _signalValue;// || interruptCaught;
    //_catchedInterruptions[_pinToRead] = false;

    return result;
  }
};

class Hardware
{
private:
  void SetupPins()
  {
    pinMode(SENSOR_PIN_1, INPUT);
    pinMode(SENSOR_PIN_2, INPUT);
    pinMode(SENSOR_PIN_3, INPUT);
    pinMode(SENSOR_PIN_4, INPUT);
    
    pinMode(RED_LIGHT_PIN, OUTPUT);
    pinMode(GREEN_LIGHT_PIN, OUTPUT);
    pinMode(YELLOW_LIGHT_PIN, OUTPUT);
  
    pinMode(IS_ACTIVE_STATUS_PIN, OUTPUT);
    pinMode(DISABLE_PIN, INPUT);
    
    pinMode(ALARM_PIN, OUTPUT);

    // Pull-down resistors are used
//    digitalWrite(DISABLE_PIN, LOW);
//    digitalWrite(SENSOR_PIN_1, LOW);
//    digitalWrite(SENSOR_PIN_2, LOW);
//    digitalWrite(SENSOR_PIN_3, LOW);
//    digitalWrite(SENSOR_PIN_4, LOW);
  }
public:
  Hardware()
  {
    SetupPins();
  
    DisableInput = new SafeInputReader(DISABLE_PIN);//, HIGH);

    TrackedInput1 = new SafeInputReader(SENSOR_PIN_1);//, HIGH);
    TrackedInput2 = new SafeInputReader(SENSOR_PIN_2);//, HIGH);
    TrackedInput3 = new SafeInputReader(SENSOR_PIN_3);//, HIGH);
    TrackedInput4 = new SafeInputReader(SENSOR_PIN_4);//, HIGH);
  }

  void SetDefaultState()
  {
    SetIsEnabledCallbackValue(HIGH);
    SetAlarmValue(LOW);
    SetRedLightValue(HIGH);
    SetYellowLightValue(HIGH);
    SetGreenLightValue(HIGH);
  }

  SafeInputReader * DisableInput;

  SafeInputReader * TrackedInput1;
  SafeInputReader * TrackedInput2;
  SafeInputReader * TrackedInput3;
  SafeInputReader * TrackedInput4;

  void SetAlarmValue(int value)
  {
    digitalWrite(ALARM_PIN, value);
  }

  void SetResetDevicesValue(int value)
  {
    digitalWrite(RESET_PIN_PEREPHERIALS, value);
  }

  void SetRedLightValue(int value)
  {
    digitalWrite(RED_LIGHT_PIN, value);
  }
  void SetGreenLightValue(int value)
  {
    digitalWrite(GREEN_LIGHT_PIN, value);
  }
  void SetYellowLightValue(int value)
  {
    digitalWrite(YELLOW_LIGHT_PIN, value);
  }
  
  void SetIsEnabledCallbackValue(int value)
  {
    digitalWrite(IS_ACTIVE_STATUS_PIN, value);
  }
};

class IState
{
public:
  //virtual ~IState() {}
  virtual int GetStateNumber() = 0;
  virtual int GetNextStateNumber() = 0;
  virtual void Start();
};

class ActivatedState : public IState
{
private:
  Hardware * _hardware;
public:
  ActivatedState(Hardware * hardware)
  {
    _hardware = hardware;
  };

  virtual void Start()
  {
    _hardware->SetIsEnabledCallbackValue(HIGH);
    _hardware->SetAlarmValue(LOW);
    _hardware->SetGreenLightValue(LOW);
    _hardware->SetYellowLightValue(HIGH);
    _hardware->SetRedLightValue(LOW);

    // temporary workaround
    if (_hardware->TrackedInput1->IsInputSwitched()
      || _hardware->TrackedInput2->IsInputSwitched()
      || _hardware->TrackedInput3->IsInputSwitched()
      || _hardware->TrackedInput4->IsInputSwitched())
    {
      // do nothing
      // this resets all fires detected by interruptions
    }

    NotifyPeripherialsActivating();
  };

  virtual int GetStateNumber()
  {
    return activatedId;
  };

  virtual int GetNextStateNumber()
  {    
    if (_hardware->DisableInput->IsInputSwitched())
    {
      return deactivatedId;
    }

    if (_hardware->TrackedInput1->IsInputSwitched()
      || _hardware->TrackedInput2->IsInputSwitched()
      || _hardware->TrackedInput3->IsInputSwitched()
      || _hardware->TrackedInput4->IsInputSwitched())
    {
      return alarmId;
    }

    return activatedId;
  };
};

class DeactivatedState : public IState
{
private:
  Hardware * _hardware;
public:
  DeactivatedState(Hardware * hardware)
  {
    _hardware = hardware;
  };

  virtual void Start()
  {
    _hardware->SetIsEnabledCallbackValue(LOW);
    _hardware->SetAlarmValue(LOW);
    _hardware->SetGreenLightValue(HIGH);
    _hardware->SetYellowLightValue(LOW);
    _hardware->SetRedLightValue(LOW);
  };

  virtual int GetStateNumber()
  {
    return deactivatedId;
  };

  virtual int GetNextStateNumber()
  {
    if (!_hardware->DisableInput->IsInputSwitched())
    {
      return  activatedId;
    }

    return deactivatedId;
  };
};


class InitializingState : public IState
{
private:
  Hardware * _hardware;
public:
  InitializingState(Hardware * hardware)
  {
    _hardware = hardware;
  };

  virtual void Start()
  {
    _hardware->SetDefaultState();
  };

  virtual int GetStateNumber()
  {
    return initializationId;
  };

  virtual int GetNextStateNumber()
  {
    NotifyPeripherialsActivating();

    _hardware->SetRedLightValue(LOW);
    _hardware->SetYellowLightValue(LOW);
    _hardware->SetGreenLightValue(LOW);

    if (_hardware->DisableInput->IsInputSwitched())
    {
      return deactivatedId;
    }
    else
    {
      return activatedId;
    }
  };
};

class AlarmState : public IState
{
private:
  Hardware * _hardware;
  unsigned long startTime;
public:
  AlarmState(Hardware * hardware)
  {
    _hardware = hardware;
  };

  virtual void Start()
  {
    _hardware->SetAlarmValue(HIGH);
    _hardware->SetGreenLightValue(LOW);
    _hardware->SetYellowLightValue(LOW);
    _hardware->SetRedLightValue(HIGH);

    startTime = millis();
  };

  virtual int GetStateNumber()
  {
    return alarmId;
  };

  virtual int GetNextStateNumber()
  {
    if (_hardware->DisableInput->IsInputSwitched())
    {
      return  deactivatedId;
    }

    if (_hardware->TrackedInput1->IsInputSwitched()
      || _hardware->TrackedInput2->IsInputSwitched()
      || _hardware->TrackedInput3->IsInputSwitched()
      || _hardware->TrackedInput4->IsInputSwitched())
    {
      startTime = millis();
      return alarmId;
    }

    unsigned long timeToWait = (long)alarmActiveSeconds * (long)1000;

    if(DEBUG)
    {
      Serial.print("Alarm left seconds: ");
      Serial.println((timeToWait - (millis() - startTime))/1000);
    }
    
    if (millis() - startTime > timeToWait)
    {
      return activatedId;
    }

    return alarmId;
  };
};

class StateManager
{
private:
  static const int _statesLen = 5;
  IState * _states[_statesLen];
  IState * _activeState = NULL;

  void StartNewState(int stateId)
  {
    if(DEBUG)
    {
      Serial.print("Starting new State: ");
      if (_activeState != NULL)
      {
        Serial.print("Current: ");
        Serial.print(_activeState->GetStateNumber());
      }
      Serial.print(", New: ");
      Serial.println(stateId);
    }
  
    IState * newActive = NULL;
    for (int i = 0; i < _statesLen; i++)
    {
      IState * state = _states[i];
      if (state != NULL && state->GetStateNumber() == stateId)
      {
        _activeState = state;
        _activeState->Start();
        break;
      }
    }
  }

public:
  StateManager()
  {
    for (int i = 0; i < _statesLen; i++)
    {
      _states[i] = NULL;
    }
  }

  void AddState(IState * newState)
  {
    for (int i = 0; i < _statesLen; i++)
    {
      if (_states[i] == NULL)
      {
        _states[i] = newState;
        break;
      }
    }
  }

  void Start(int stateId)
  {
    StartNewState(stateId);
  }

  void Refresh()
  {
    int newStateId = _activeState->GetNextStateNumber();
    
    if (DEBUG)
    {
        Serial.print("Refresh: ");
        Serial.print("Current State = ");
        Serial.print(_activeState->GetStateNumber());
        Serial.print(", Next: ");
        Serial.println(newStateId);
    }
      
    if (newStateId != _activeState->GetStateNumber())
    {
      StartNewState(newStateId);
    }
  }

};

Hardware * hardware = NULL;
StateManager * stateManager = NULL;

void NotifyPeripherialsActivating()
{
  hardware->SetResetDevicesValue(HIGH);
  delay(resetDelayMillis);
  hardware->SetResetDevicesValue(LOW);
  delay(resetDelayMillis);
}

void setup()
{
  if (DEBUG)
  {
    Serial.begin(9600);
  }
  
  hardware = new Hardware();
  hardware->SetDefaultState();
  stateManager = new StateManager();

  stateManager->AddState(new InitializingState(hardware));
  stateManager->AddState(new ActivatedState(hardware));
  stateManager->AddState(new DeactivatedState(hardware));
  stateManager->AddState(new AlarmState(hardware));
  stateManager->Start(initializationId);
}

void loop()
{
  delay(loopDelay);
  stateManager->Refresh();
}
