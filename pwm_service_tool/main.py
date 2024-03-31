# screen lib ref:
# https://pypi.org/project/micropython-i2c-lcd/
# https://github.com/brainelectronics/micropython-i2c-lcd/tree/main/lcd_i2c

# ampy --port COM5 run main.py

from lcd_i2c import LCD
from machine import I2C, Pin, ADC, PWM
import time


MODE_DEMO = 0
MODE_READING = 1
MODE_GENERATING_FREQ = 2
MODE_GENERATING_DUTY = 3
MODE_SERIAL_SAMPLING = 4


# adc_a = ADC(32)
adc_b = ADC(33)
# val = adc.read_u16()  # read a raw analog value in the range 0-65535
# val_4 = adc.read_uv()   # read an analog value in microvolts


class PDisplay:
    def __init__(self, sda_pin, scl_pin):
        I2C_ADDR = 0x27  # DEC 39, HEX 0x27
        self.NUM_ROWS = 2
        self.NUM_COLS = 16
        i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=800000)
        self.lcd = LCD(addr=I2C_ADDR, cols=self.NUM_COLS, rows=self.NUM_ROWS, i2c=i2c)
        self.lcd.begin()
        self.line_a = ""
        self.line_b = ""

    def _update(self):
        self.lcd.cursor_position = (0, 0)
        self.lcd.print(self.line_a + " " * self.NUM_COLS)
        self.lcd.cursor_position = (0, 1)
        self.lcd.print(self.line_b + " " * self.NUM_COLS)

    def set_state(self, line_a, line_b):
        self.line_a = line_a
        self.line_b = line_b

        self._update()


class PButton:
    def __init__(self, pin_number):
        ts = time.ticks_ms()
        self.pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        self.update_ts = ts
        self.last_high_ts = ts - 1000
        self.last_low_ts = ts - 1
        self.confirmed_unpressed_ts = ts
        self.click_picked_ts = ts

    def update(self):
        ts = time.ticks_ms()
        self.update_ts = ts
        if self.pin.value():
            self.last_high_ts = ts
        else:
            self.last_low_ts = ts

        if self.update_ts - self.last_low_ts > 50:
            self.confirmed_unpressed_ts = ts

    def is_pressed(self):
        return self.update_ts - self.last_low_ts < 50

    def get_long_press_duration(self):
        if self.confirmed_unpressed_ts == self.update_ts:
            return 0

        return self.update_ts - self.confirmed_unpressed_ts

    def check_click_once(self):
        new_click = self.is_pressed() and self.click_picked_ts < self.confirmed_unpressed_ts
        if new_click:
            self.click_picked_ts = self.confirmed_unpressed_ts
        return new_click


display = PDisplay(21, 22)
button_a = PButton(16)


# create testing PWM
p12 = Pin(12)
pwm12 = PWM(p12)
pwm12.freq(50)
# pwm12.duty(512)
pwm12.duty(900)


state = {
    "modeChanged": True,
    "demo_test": 0.0,
    "reading": {
        "window_start_ts": 0,
        "timestamps": [],
        "readings": []
    },
    "sampling": {
        "window_start_ts": 0,
        "timestamps": [],
        "readings": [],
        "completed": False
    }
}


def get_v_reading():
    val_b = ((adc_b.read_u16() * 5.0) / 52000) * 4  # adjusted for voltage divider
    return val_b


def process_demo(tick_ms):
    init = state["modeChanged"]
    state["modeChanged"] = False

    if init:
        state["demo_test"] = 0

    state["demo_test"] += .1
    display.set_state(str("Demo"), str(state["demo_test"]))


def process_serial_sampling(tick_ms):
    init = state["modeChanged"]
    state["modeChanged"] = False

    if init:
        display.set_state(str("Serial"), str("Sampling..."))
        state["sampling"]["window_start_ts"] = tick_ms
        state["sampling"]["timestamps"] = []
        state["sampling"]["readings"] = []
        state["sampling"]["completed"] = False

    if state["sampling"]["completed"]:
        return

    start_delay = 1000
    sample_duration = 500

    if tick_ms - state["sampling"]["window_start_ts"] < start_delay:
        return

    val_b = get_v_reading()
    state["sampling"]["timestamps"].append(tick_ms)
    state["sampling"]["readings"].append(val_b)

    if tick_ms - state["sampling"]["window_start_ts"] > start_delay + sample_duration:
        for i, r in enumerate(state["sampling"]["readings"]):
            print(str(state["sampling"]["timestamps"][i]) + "|" + "{:.2f}".format(r))

        state["sampling"]["completed"] = True

        display.set_state(str("Completed"), str(""))


def process_reading(tick_ms):
    init = state["modeChanged"]
    state["modeChanged"] = False

    if init:
        display.set_state(str("RX_ ..."), str(""))
        state["reading"]["window_start_ts"] = tick_ms
        state["reading"]["timestamps"] = []
        state["reading"]["readings"] = []

    val_b = get_v_reading()
    state["reading"]["timestamps"].append(tick_ms)
    state["reading"]["readings"].append(val_b)

    w_duration = 500
    if tick_ms - state["reading"]["window_start_ts"] > w_duration:
        readings = state["reading"]["readings"]
        sorted_readings = list(readings)
        sorted_readings.sort()
        hv = sorted_readings[int(len(sorted_readings) * 0.9)]
        v_threshold = hv / 2
        if v_threshold < 1:
            v_threshold = 1

        r_count = len(readings)
        h_r_count = 0
        j_count = 0
        for i, r in enumerate(readings):
            if r > v_threshold:
                h_r_count += 1

                if i > 0 and readings[i -1] <= v_threshold:
                    j_count += 1

        duty = (h_r_count / r_count) * 100
        frequency = j_count / (w_duration / 1000)

        # display.set_state(str("RX: Duty " + "{:.1f}".format(duty) + " %"), str("Freq. " + "{:.1f}".format(frequency) + " Hz"))
        display.set_state(str("RX_ Duty: " + "{:.1f}".format(duty) + "%"), str("{:.1f}".format(hv) + "V" + "  " + "{:.1f}".format(frequency) + "Hz"))
        # display.set_state(str("RX_ Duty: " + "{:.1f}".format(duty) + "%"), "High: " + str("{:.1f}".format(hv) + "V"))
        # display.set_state(str("RX_ Duty: " + "{:.1f}".format(duty) + "%"), str(r_count))

        state["reading"]["window_start_ts"] = time.ticks_ms()
        state["reading"]["timestamps"] = []
        state["reading"]["readings"] = []


modes = {
    # MODE_DEMO: process_demo,
    MODE_READING: process_reading,
    MODE_SERIAL_SAMPLING: process_serial_sampling
}
current_mode = MODE_READING

cycle_count = 0
while True:
    tick_ms = time.ticks_ms()

    if cycle_count % 50 == 0:
        button_a.update()

    # is_pressed = button_a.is_pressed()
    # lp_duration = button_a.get_long_press_duration()

    if button_a.check_click_once():
        idx = list(modes.keys()).index(current_mode)
        mode_keys = list(modes.keys()) * 2
        current_mode = mode_keys[idx + 1]
        state["modeChanged"] = True

    modes[current_mode](tick_ms)

    cycle_count += 1
    if cycle_count == 100000:
        cycle_count = 0

