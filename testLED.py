from machine import Pin
import utime

LED = Pin("LED", Pin.OUT)


LED.value(1)  # Turn the LED on
utime.sleep(1)
LED.value(0)  # Turn the LED off