

# based on official examples:
# https://github.com/micropython/micropython/blob/v1.12/examples/bluetooth/ble_uart_peripheral.py

# NOTE: there is a newer version:
# https://github.com/micropython/micropython/blob/v1.21.0/examples/bluetooth/ble_uart_peripheral.py


import json
import bluetooth
from micropython import const
import struct
from machine import Pin, PWM
import time



pwm_a_pin = 25
motor_a_fwd_pin = 32
motor_a_bckwd_pin = 33
pwm_b_pin = 5
motor_b_fwd_pin = 18
motor_b_bckwd_pin = 19


p111 = Pin(motor_a_fwd_pin, Pin.OUT)
p112 = Pin(motor_a_bckwd_pin, Pin.OUT)
p113 = PWM(Pin(pwm_a_pin, mode=Pin.OUT))
p113.freq(2000) # up to 10 KHz
p211 = Pin(motor_b_fwd_pin, Pin.OUT)
p212 = Pin(motor_b_bckwd_pin, Pin.OUT)
p213 = PWM(Pin(pwm_b_pin, mode=Pin.OUT))
p213.freq(2000) # up to 10 KHz


tracks_state = {
    "track_a_power": 0.0,
    "track_a_direction": 0,
    "track_a_timeout": 0,
    "track_b_power": 0.0,
    "track_b_direction": 0,
    "track_b_timeout": 0
    }


def update_state_from_string(state_string):
    current_time = time.ticks_ms()

    try:
        a_spec = state_string.split('||')[0]
        b_spec = state_string.split('||')[1]
        tracks_state["track_a_power"] = float(a_spec.split('|')[0])
        tracks_state["track_a_direction"] = int(a_spec.split('|')[1])
        tracks_state["track_a_timeout"] = current_time + int(a_spec.split('|')[2])
        tracks_state["track_b_power"] = float(b_spec.split('|')[0])
        tracks_state["track_b_direction"] = int(b_spec.split('|')[1])
        tracks_state["track_b_timeout"] = current_time + int(b_spec.split('|')[2])
    except:
        print("Failed to process new state: " + state_string)


def update_motors():
    current_time = time.ticks_ms()

    if current_time < tracks_state["track_a_timeout"]:
        p113.duty(int(tracks_state["track_a_power"] * 1022))  # 0 to 1023 (0% - 100% width)
        p111.value(1 if tracks_state["track_a_direction"] == 1 else 0)
        p112.value(1 if tracks_state["track_a_direction"] == -1 else 0)
    else:
        p111.value(0)
        p112.value(0)

    if current_time < tracks_state["track_b_timeout"]:
        p213.duty(int(tracks_state["track_b_power"] * 1022))  # 0 to 1023 (0% - 100% width)
        p211.value(1 if tracks_state["track_b_direction"] == 1 else 0)
        p212.value(1 if tracks_state["track_b_direction"] == -1 else 0)
    else:
        p211.value(0)
        p212.value(0)


# Advertising payloads are repeated packets of the following form:
#   1 byte data length (N + 1)
#   1 byte type (see constants below)
#   N bytes type-specific data

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID32_MORE = const(0x4)
_ADV_TYPE_UUID128_MORE = const(0x6)
_ADV_TYPE_APPEARANCE = const(0x19)


# Generate a payload to be passed to gap_advertise(adv_data=...).
def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack('BB', len(value) + 1, adv_type) + value

    _append(_ADV_TYPE_FLAGS, struct.pack('B', (0x01 if limited_disc else 0x02) + (0x00 if br_edr else 0x04)))

    if name:
        _append(_ADV_TYPE_NAME, name)

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 4:
                _append(_ADV_TYPE_UUID32_COMPLETE, b)
            elif len(b) == 16:
                _append(_ADV_TYPE_UUID128_COMPLETE, b)

    # See org.bluetooth.characteristic.gap.appearance.xml
    _append(_ADV_TYPE_APPEARANCE, struct.pack('<h', appearance))

    return payload


def decode_field(payload, adv_type):
    i = 0
    result = []
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            result.append(payload[i + 2:i + payload[i] + 1])
        i += 1 + payload[i]
    return result


def decode_name(payload):
    n = decode_field(payload, _ADV_TYPE_NAME)
    return str(n[0], 'utf-8') if n else ''


def decode_services(payload):
    services = []
    for u in decode_field(payload, _ADV_TYPE_UUID16_COMPLETE):
        services.append(bluetooth.UUID(struct.unpack('<h', u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID32_COMPLETE):
        services.append(bluetooth.UUID(struct.unpack('<d', u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID128_COMPLETE):
        services.append(bluetooth.UUID(u))
    return services


_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE        = const(3)

_UART_UUID = bluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
_UART_TX = (bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E'), bluetooth.FLAG_NOTIFY,)
_UART_RX = (bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E'), bluetooth.FLAG_WRITE,)
_UART_SERVICE = (_UART_UUID, (_UART_TX, _UART_RX,),)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_COMPUTER = const(128)

class BLEUART:
    def __init__(self, ble, name='rchs01', rxbuf=100):
        self._ble = ble
        self._ble.active(True)
        # self._ble.irq(handler=self._irq)
        self._ble.irq(self._irq)
        ((self._tx_handle, self._rx_handle,),) = self._ble.gatts_register_services((_UART_SERVICE,))
        # Increase the size of the rx buffer and enable append mode.
        self._ble.gatts_set_buffer(self._rx_handle, rxbuf, True)
        self._connections = set()
        self._rx_buffer = bytearray()
        self._handler = None
        # Optionally add services=[_UART_UUID], but this is likely to make the payload too large.
        self._payload = advertising_payload(name=name, appearance=_ADV_APPEARANCE_GENERIC_COMPUTER)
        self._advertise()

    def irq(self, handler):
        self._handler = handler

    def _irq(self, event, data):
        print("IRQ Event: " + str(event))

        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _, = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _, = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle, = data
            if conn_handle in self._connections and value_handle == self._rx_handle:
                self._rx_buffer += self._ble.gatts_read(self._rx_handle)
                if self._handler:
                    self._handler()

    def any(self):
        return len(self._rx_buffer)

    def read(self, sz=None):
        if not sz:
            sz = len(self._rx_buffer)
        result = self._rx_buffer[0:sz]
        self._rx_buffer = self._rx_buffer[sz:]
        return result

    def write(self, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._tx_handle, data)

    def close(self):
        for conn_handle in self._connections:
            self._ble.gap_disconnect(conn_handle)
        self._connections.clear()

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)


def run():
    ble = bluetooth.BLE()
    uart = BLEUART(ble)
    print(ble.config('mac'))

    def on_rx():
        received_data = uart.read().decode().strip()
        print('__rx: ', received_data)

        update_state_from_string(received_data)

    uart.irq(handler=on_rx)

    try:
        while True:
            time.sleep_ms(50)
            update_motors()
    except KeyboardInterrupt:
        pass

    uart.close()


run()
