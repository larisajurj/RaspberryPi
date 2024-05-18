import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)  # Use physical pin numbering

# Set up GPIO pin 40 as input with pull-down resistor
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Set up GPIO pin 35 as output
GPIO.setup(19, GPIO.OUT)

while True:  # Run forever
    if GPIO.input(21) == GPIO.HIGH:
        print("Button was pushed!")

        # Toggle GPIO pin 35 state
        if GPIO.input(19) == GPIO.LOW:
            GPIO.output(19, GPIO.HIGH)
        else:
            GPIO.output(19, GPIO.LOW)

        time.sleep(1)  # Optional: Add a small delay to debounce button press
