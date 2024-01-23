

# https://dronebotworkshop.com/esp32cam-robot-car/

from micropython import const
from machine import Pin, PWM


pwm_a_pin = 25
motor_a_fwd_pin = 32
motor_a_bckwd_pin = 33


pwm_b_pin = 5 #25
motor_b_fwd_pin = 18 #32
motor_b_bckwd_pin = 19 #33


p111 = Pin(motor_a_fwd_pin, Pin.OUT)
p112 = Pin(motor_a_bckwd_pin, Pin.OUT)
p113 = PWM(Pin(pwm_a_pin, mode=Pin.OUT))
p113.freq(2000) # up to 10 KHz


p211 = Pin(motor_b_fwd_pin, Pin.OUT)
p212 = Pin(motor_b_bckwd_pin, Pin.OUT)
p213 = PWM(Pin(pwm_b_pin, mode=Pin.OUT))
p213.freq(2000) # up to 10 KHz


p113.duty(500) # 0 to 1023 (0% - 100% width)
p111.value(0)
p112.value(1)

p213.duty(500) # 0 to 1023 (0% - 100% width)
p211.value(0)
p212.value(1)
