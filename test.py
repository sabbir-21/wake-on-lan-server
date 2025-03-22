import time
from machine import Pin

led = Pin("LED", Pin.OUT)

while True:
    led.value(True)
    time.sleep(2)
    led.value(False)
