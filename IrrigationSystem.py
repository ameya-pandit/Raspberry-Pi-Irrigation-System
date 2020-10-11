import urllib.request
import codecs
import csv
from threading import Thread
import datetime, time

import RPi.GPIO as GPIO
import Freenove_DHT as DHT_sensor
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD

global startTime
global retrievedETO #retrieved ETO value from the CIMIS station
retrievedETO = 0
global retrievedAirTemp #retrieved air temperature value from the CIMIS station
retrievedAirTemp = 0
global retrievedHumidity    #retrieved humidity value from the CIMIS station
retrievedHumidity = 0

global localTemp    #local temperature measured by the DHT
localTemp = 0
global localHum     #local humidity measured by the DHT
localHum = 0

global localTempList    #used to calculate averages for temperature and humidity
localTempList = []
global localHumList
localHumList = []

global avgLocalTemp     #average local temperature and humidity values used for scaling factor calculations
avgLocalTemp = 0
global avgLocalHum
avgLocalHum = 0

global scalingHum   #using humidity for scaling factor
scalingHum = 0
global calculatedETO
calculatedETO = 0

global dataAvailableFlag    #if appropriate data is available (can then do analysis)
#dataAvailableFlag = False
global CIMISWater       #water needed per CIMIS data
CIMISWater = 0
global localWater       #water needed per local data
localWater = 0
global waterSaving      #water savings between local water usage and CIMIS water usage
waterSaving = 0

global LCDString1       #top string LCD
LCDString1 = ""
global LCDString2       #bottom string LCD
LCDString2 = ""
global waitingString    #waiting for appropriate data
waitingString = "Waiting for appropriate data..."

#GPIO pins for the components
DHTsensorPin = 11
ledPin = 12
infSensorPin = 22

def setup():    #sets up the environment
    #print("start of program")
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(DHTsensorPin, GPIO.IN)
    GPIO.setup(ledPin, GPIO.OUT)
    GPIO.output(ledPin, GPIO.LOW)
    GPIO.setup(infSensorPin, GPIO.IN)
    
    mcp.output(3, 1)
    lcd.begin(16, 2)
    lcd.clear()
        
    
def getCIMISData(): #gets CIMIS Data from Website
    global retrievedETO
    global retrievedAirTemp
    global retrievedHumidity
    
    global CIMISWater
    global LCDString1
    
    while True:
        ftp = urllib.request.urlopen("ftp://ftpcimis.water.ca.gov/pub2/hourly/hourly104.csv")
        csv_file = list(csv.reader(codecs.iterdecode(ftp, 'utf-8')))

        for line in reversed(csv_file):
            if "--" not in line:
                dateRetrieved = line[1]
                timeRetrieved = line[2]
                retrievedETO = line[4]
                #retrievedETO = 0.03 #<------------------------- TEST NUMBER
                retrievedAirTemp = line[12]
                retrievedHumidity = line[14]
                
                #print("date: {} time: {}".format(dateRetrieved, timeRetrieved))
                #print("eto: {} air temp: {} hum: {}".format(retrievedETO, retrievedAirTemp, retrievedHumidity))
                
                
                CIMISWater = float(retrievedETO) * 1.0 * 200 * 0.62 / 0.75
                
                break
        
        convTimeRet = int(int(timeRetrieved) / 100)
        #convTimeRet = 24
        
        #Not really useful for assignment but I used this for testing/something cool
        if (convTimeRet < 12):
            lastUpdateString = "Last CIMIS Update at: {} AM".format(convTimeRet)
            #print(lastUpdateString)
        elif (convTimeRet == 12):
            lastUpdateString = "Last CIMIS Update at: 12 PM"
            #print(lastUpdateString)
        elif (convTimeRet == 24):
            lastUpdateString = "Last CIMIS Update at: 12 AM"
            #print(lastUpdateString)
        else:
            lastUpdateString = "Last CIMIS Update at: {} PM".format(convTimeRet-12)
            #print(lastUpdateString)
            
        #print(datetime.datetime.now().strftime("%H:%M:%S"))
        
        time.sleep(3600) #<----------- CHANGE TO 3600

def getDHTData():   #getting data from the DHT sensor
    time.sleep(4)
    global localTemp
    global localHum
    
    global avgLocalTemp
    global avgLocalHum
    
    global retrievedETO
    global retrievedAirTemp
    global retrievedHumidity
    
    global scalingHum
    global calculatedETO
    
    global dataAvailableFlag
    dataAvailableFlag = False
    
    firstDataFlag = False
    
    global CIMISWater
    global localWater
    global waterSaving
    
    global LCDString1
    
    dht = DHT_sensor.DHT(DHTsensorPin)
    
    while (True):
        chk = dht.readDHT11()
        #print(chk)
        
        #print("retrievedHum: {}".format(retrievedHumidity))
    
        if (chk is dht.DHTLIB_OK and (dht.temperature <= 100 and dht.humidity <= 100)): #if appropriate value
            localTemp = 1.8*dht.temperature + 32
            localHum = dht.humidity
            
            #print("temperature: {} humidity: {}".format(localTemp, localHum))
            
            if (localTemp <= 150 and localHum <= 100):
                #round(localTemp, 2)
                #round(localHum, 2)
                
                #print("T: {:.1f} H: {:.1f}".format(localTemp, localHum))
                
                localTempList.append(localTemp)
                localHumList.append(localHum)
                
                avgLocalTemp = sum(localTempList) / len(localTempList)
                avgLocalHum = sum(localHumList) / len(localHumList)
                
                #scalingTemp = float(retrievedAirTemp) / avgLocalTemp
                scalingHum = float(retrievedHumidity) / avgLocalHum
                
                #if (firstDataFlag == False):
                #    firstDataFlag = True
                #print("avg local: {}".format(avgLocalHum))
                #scalingFactor = (scalingTemp + scalingHum)/2
                
                #print("SCALINGTemp: {} Hum: {} Factor: {}".format(scalingTemp, scalingHum, scalingFactor))
            
                #POTENTIAL WORKAROUND
                    #USE CIMIS VALUE TILL U HAVE A NON ZERO SCALE
            
            #print("retrieved ETO: {}".format(retrievedETO))
        else:   #if not appropriate value try again in 2 seconds
            #print(datetime.datetime.now().strftime("%H:%M:%S"))
            time.sleep(2)
            continue
            
        if (scalingHum != 0):   #if we have data to then do analysis
            dataAvailableFlag = True
            #print("condition")
            calculatedETO = float(retrievedETO) / scalingHum
            #print("calculatedETO: {}".format(calculatedETO))
            
            localWater = calculatedETO * 1.0 * 200 * 0.62 / 0.75
            waterSaving = CIMISWater - localWater
            
            LCDString1 = "CIM Temp:{} Loc Temp:{:.1f} CIM Hum:{} Loc Hum:{:.1f} CIMIS ET: {} Loc ET:{:.2f} H2O Sav:{:.3f}".format(float(retrievedAirTemp), avgLocalTemp, float(retrievedHumidity), avgLocalHum, float(retrievedETO), float(calculatedETO), float(waterSaving))
            #print(LCDString1)
            
            #print("CIMIS Water: {} Local Water: {} Water Saving: {}".format(CIMISWater, localWater, waterSaving))
            
            
                    
        #print(datetime.datetime.now().strftime("%H:%M:%S"))
        #print("scalingHum: {}".format(scalingHum))
        
        #print(localTempList)
        #print(localHumList)
        
        #print("avg temp: {} avg hum: {}". format(avgLocalTemp, avgLocalHum))
        
        #if (firstDataFlag == False):
        #    time.sleep(5)
        #else:
        #    time.sleep(30)
        time.sleep(60)  #sleep for 60 seconds (get DHT data every minute)

def printToLCD():
    time.sleep(5)
    
    global dataAvailableFlag
    
    global waterSaving
    
    global LCDString1
    global LCDString2
    global waitingString
    
    #counters used to display certain part of string
    count = 0
    count2 = 0
    
    lcd.setCursor(0, 0)
    lcd.clear()
    
    while True:
        count += 1
        count2 += 1
        if (dataAvailableFlag == True):
            #lcd.message("T:{:.2f} H:{}".format(localTemp, localHum))
           
            if(len(LCDString1[count:]) < 16):
                count = 0
                
            lcd.message(LCDString1[count:count+15] + '\n')
            
            lcd.setCursor(0, 1)
            #print(LCDString2)
            if(len(LCDString2[count2:]) < 16):
                count2 = 0
            
            lcd.message(LCDString2[count2:count2+15] + '\n')
            
        else:
            if(len(waitingString[count:]) < 16):
                count = 0
                
            lcd.message(waitingString[count:count+15] + '\n')
                                
        time.sleep(0.2) #update LCD every 0.2 seconds (so that it appears as if there is rotating messages
        lcd.clear()
        
def waterOnOff():   #acts as the relay
    time.sleep(5)
    global localWater
    global dataAvailableFlag
    global LCDString2
    waterCount = 0
    noMotionCount = 0
    wateringCount = 0
    timeLeft = 0
    waterFlag = False
    waterOn = False
    waterDone = False
    howManyWater = 0    #how many times have you watered? not really that useful

    while True:
        if (dataAvailableFlag == True): #if data is available, then proceed
            #print("how many water: ", howManyWater);
            waterCount += 1 #counter used for testing (acts like a second)
            #print("waterCount: ", waterCount)
            
            if (waterFlag == False and waterCount == 20):   #20 seconds into the hour (can then do watering)
                timeWater = float(localWater/1020*3600)+1
                LCDString2 = "Water Time: {:.1f}".format(timeWater)
                #print("time for watering: ", timeWater)
                waterFlag = True
            
            if (GPIO.input(infSensorPin) == GPIO.LOW):
                if (waterFlag == True):
                    noMotionCount += 1
                    #print("no motion: ", noMotionCount)
                    
                    if (noMotionCount > 5 and waterDone == False):  #if no motion for 5 seconds and if area not yet watered
                        GPIO.output(ledPin, GPIO.HIGH)
                        LCDString2 = "Watering..."
                        #print("watering...")
                        wateringCount += 1
                        waterOn = True
                        
                        if (wateringCount > int(timeWater)):    #if done watering
                            LCDString2 = "Done Watering!"
                            howManyWater += 1
                            #print("done watering")
                            GPIO.output(ledPin, GPIO.LOW)
                            waterOn = False
                            waterDone = True
                            wateringCount = 0
            
            if (GPIO.input(infSensorPin) == GPIO.HIGH): #if motion detected
                #print("motion detected")
                
                noMotionCount = 0
                if (waterOn == True):   #if motion detected when watering
                    GPIO.output(ledPin, GPIO.LOW)
                    #noMotionCount = 0
                    #print("watering count: ", wateringCount)
                    LCDString2 = "Motion! Water Stopped "
                    #print("motion detected, watering stopped")
                    waterOn = False
                
        if (waterCount == 3600):    #reset parameters every hour
            waterFlag = False
            waterDone = False
            LCDString2 = ""
            waterCount = 0
            noMotionCount = 0
            
        time.sleep(1)   #acts like a second

def run():  #spawns all the daemon thraeds with all the functions needed to run the system
    getDHTDataThread = Thread(target=getDHTData)
    getCIMISDataThread = Thread(target=getCIMISData);
    printToLCDThread = Thread(target=printToLCD)
    waterOnOffThread = Thread(target=waterOnOff)
    
    getDHTDataThread.daemon = True
    getCIMISDataThread.daemon = True
    printToLCDThread.daemon = True
    waterOnOffThread.daemon = True
    
    getDHTDataThread.start()
    getCIMISDataThread.start()
    printToLCDThread.start()
    waterOnOffThread.start()
    
    while True:
        pass
    
#TAKEN FROM FREENOVE GUIDE
PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
# Create PCF8574 GPIO adapter.
try:
    mcp = PCF8574_GPIO(PCF8574_address)
except:
    try:
        mcp = PCF8574_GPIO(PCF8574A_address)
    except:
        print ('I2C Address Error !')
        exit(1)
# Create LCD, passing in MCP GPIO adapter.
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=mcp)

if __name__ == '__main__':
    startTime = datetime.datetime.now().strftime("%H:%M:%S")
    setup()
    run()


