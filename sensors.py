import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD
import time
import board
import adafruit_dht
import busio
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1015 as ADS
import threading
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Use a service account.
cred = credentials.Certificate('private-key.json')

app = firebase_admin.initialize_app(cred)

db = firestore.client()



#FIREBASE SETUP
config = {
    "apiKey": "AIzaSyC1d-x5s-DHPTIzARn7A59Kt8QjAfakO-s",
    "authDomain": "rpi-lab-project",
    "databaseURL": "https://rpi-lab-project-default-rtdb.firebaseio.com/",
    "storageBucket": "rpi-dht-monitor.appspot.com"
}
#firebase = pyrebase.initialize_app(config)
#db = firebase.database()

#LCD SETUP
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=3, cols=16, rows=2, dotsize=8)
lcd.clear()

# Define custom characters
bec1 = (
    0b00111,
    0b01000,
    0b10000,
    0b10010,
    0b10001,
    0b01001,
    0b00111,
    0b00011,
)
bec2 = (
    0b11000,
    0b00100,
    0b00010,
    0b10010,
    0b00010,
    0b00100,
    0b11000,
    0b10000,
)
nor1 = (
	0b00000,
	0b00000,
	0b00001,
	0b01101,
	0b10010,
	0b10000,
	0b01111,
	0b00000
)

nor2 = (
	0b00000,
	0b11000,
	0b00100,
	0b00100,
	0b00011,
	0b00001,
	0b11110,
	0b00000
)
strop1 = (
	0b00000,
	0b00001,
	0b11001,
	0b01010,
	0b00110,
	0b10010,
	0b10001,
	0b00000
)
strop2 = (
    0b11000,
	0b00100,
	0b11100,
	0b00010,
	0b00010,
	0b00010,
	0b11100,
	0b00000
)
soare1 = (
    0b00010,
	0b00100,
	0b10000,
	0b11011,
	0b11000,
	0b10000,
	0b00100,
	0b00010
)
soare2 = (
    0b01000,
	0b00100,
	0b00001,
	0b11011,
	0b00011,
	0b00001,
	0b00100,
	0b01000
)
# Create custom characters
lcd.create_char(0, bec1)
lcd.create_char(1, bec2)
lcd.create_char(2, nor1)
lcd.create_char(3, nor2)
lcd.create_char(4, soare2)
lcd.create_char(5, soare1)
lcd.create_char(6, strop1)
lcd.create_char(7, strop2)

# Clear the display again after creating characters
lcd.clear()

# Set cursor to desired position
lcd.cursor_pos = (0, 0)


#DHT SENSOR SETUP
dhtDevice = adafruit_dht.DHT22(board.D17, use_pulseio = False)

#GPIO SETUP
GPIO.setmode(GPIO.BCM)

#WATER SENSOR SETUP
ldr_pin = 22 
GPIO.setup(ldr_pin, GPIO.IN)

#BLUE LED SETUP
blue_led_pin = 26
GPIO.setup(blue_led_pin, GPIO.OUT)

#YELLOW LED SETUP
yellow_led_pin = 19
GPIO.setup(yellow_led_pin, GPIO.OUT)

#RED LED SETUP
red_led_pin = 19
GPIO.setup(red_led_pin, GPIO.OUT)

#BUTTON SETUP
button_pin = 21
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


#ADC SETUP
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1015(i2c)
chan = AnalogIn(ads, ADS.P0)
minValue = 8000  # Corresponds to super wet
maxValue = 26300 # Corresponds to super dry

#Defining the duration between actions
time_realtime_db = 5 #data will be send to realtime db every 5 sec
time_firestore = 6 #data will be send to firestore evry 5*6 sec

def button_handler():
    while True:
        if GPIO.input(button_pin) == GPIO.HIGH:
            print("Button was pushed!")

            # Toggle LED state
            if GPIO.input(yellow_led_pin) == GPIO.LOW:
                GPIO.output(yellow_led_pin, GPIO.HIGH)
            else:
                GPIO.output(yellow_led_pin, GPIO.LOW)

            time.sleep(1)
        
def sensor_monitor():
    while True:
        try:
            #The "Light LED" data in firebase is set on true from the
            #app when the user presses the button
            #At the start of each cycle we check that value to be
            #light up the LED if needed 
            
            #light_led = db.child("Light_LED").get().val()        
            light_led = realtime_db.reference('Light_LED').get()

            sensorValue = chan.value
            wetnessScore = 1 + 9 * (maxValue - sensorValue) / (maxValue - minValue)
            if wetnessScore < 1:
                wetnessScore = 1
            elif wetnessScore > 10:
                wetnessScore = 10
            # Check inputs every 10 seconds
            light_state = GPIO.input(ldr_pin)
            
            
            temperature_c = dhtDevice.temperature
            temperature_f = temperature_c * (9 / 5) + 32
            humidity = dhtDevice.humidity
            print(
                "Temp: {:.1f} F / {:.1f} C    Humidity: {}% ".format(
                    temperature_f, temperature_c, humidity
                )
            )

            if light_state:
                print("Light is NOT present!")

            else:
                print("Light is present!")

            if light_led:
                print("Service needed called")
                GPIO.output(blue_led_pin, GPIO.HIGH)
            else:
                print("Water Detected!")
                GPIO.output(blue_led_pin, GPIO.LOW)
            
            data = {
            "Light_detected" : not light_state,
            "Water_detected" : round(wetnessScore,2),
            "Temp" : temperature_c,
            "Humidity" : humidity
            }
            
            lcd.clear()

            if light_led:
                LCD_print("user_called", 0,0,0,0)
            else:
                LCD_print("status", not light_state, humidity, temperature_c, round(wetnessScore))
            #db.child("Status").push(data)
            #db.update(data)
            realtime_db.reference('Status').push(data)
            realtime_db.reference().update(data)

            time.sleep(5)

        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard to read, just keep going
            print(error.args[0])
            time.sleep(2.0)
            continue
        #except Exception as error:
         #   dhtDevice.exit()
          #  raise error
        except KeyboardInterrupt as error:
            GPIO.cleanup()

def send_to_firestore(humidity, temperature_c, wetnessScore, light_state):
    firestore_data = {
                "sampling_time": firestore.SERVER_TIMESTAMP,
                "humidity": humidity,
                "temperature": temperature_c,
                "wetness_score": wetnessScore,
                "light": not light_state
            }
    db_firestore.collection('SensorData').add(firestore_data)
    
    
#We define a function manage the display
#The LCD can have two modes based on the alert_type
#   1. user_called: prints "Service needed!"
#   2. status: the normal mode, displays the data from sensors

def LCD_print(alert_type, light, humidity, temp, wetnessScore):
    if alert_type == "user_called":
        lcd.write_string('Service needed!')
    else:
        # Set cursor to desired position
        light_string = format(int(light), 'b')
        print(light_string)
        humidity_string = "{}% ".format(humidity)
        print(humidity_string)
        temp_string = "{:.1f}C  ".format(temp)
        print(temp_string)
        wetnessScore_string = str(wetnessScore)
        print(wetnessScore_string)
        # Write the custom characters
        
        lcd.cursor_pos = (0, 1)

        #Light custom character
        lcd.write_string('\x00')  
        lcd.write_string('\x01:')
        lcd.write_string(light_string)
        lcd.cursor_pos = (0, 7)

        
        #Humidity custom character
        lcd.write_string('\x02')  
        lcd.write_string('\x03:')
        lcd.write_string(humidity_string)
        
        lcd.cursor_pos = (1, 1)
        
        #Wetness custom character
        lcd.write_string('\x06')
        lcd.write_string('\x07:')
        lcd.write_string(wetnessScore_string)
        
        lcd.cursor_pos = (1, 7)
        #Temperature custom character
        lcd.write_string('\x04')
        lcd.write_string('\x05:')
        lcd.write_string(temp_string)
        
#Create threads for button handling and sensor monitoring
button_thread = threading.Thread(target=button_handler)
sensor_thread = threading.Thread(target=sensor_monitor)

# Start the threads
button_thread.start()
sensor_thread.start()

# Join the threads (wait for them to finish)
button_thread.join()
sensor_thread.join()