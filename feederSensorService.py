#!/var/www/feeder/bin/python
import sys

sys.path.extend(['/var/www/feeder/feeder'])
import logging.handlers
import argparse
import time 
import signal
import commonTasks
import RPi.GPIO as GPIO
import datetime
import configparser
import os

#Achar arquivos
dir = os.path.dirname(__file__)
configFilePath = os.path.abspath(os.path.join(dir, "app.cfg"))
configParser = configparser.RawConfigParser()
configParser.read(configFilePath)

#Achar variavies
feedSensorGPIO = configParser.get('feederConfig', 'Sensor_Button_GPIO')
LOG_SensorService_FILENAME = configParser.get('feederConfig', 'Log_SensorService_Filename')
delayBetweenButtonPushes = configParser.get('feederConfig', 'Seconds_Delay_After_Button_Push')

parser = argparse.ArgumentParser(description="My simple Python service")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_SensorService_FILENAME + "')")

args = parser.parse_args()
if args.log:
    LOG_FILENAME = args.log

# Cria logs a meia noite, mantendo os dos ultimos 3 dias
logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO) 

handler = logging.handlers.TimedRotatingFileHandler(LOG_SensorService_FILENAME, when="midnight", backupCount=3)

formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)



class MyLogger(object):
    def __init__(self, logger, level):
        """Needs a logger and a logger level."""
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())



sys.stdout = MyLogger(logger, logging.INFO)

sys.stderr = MyLogger(logger, logging.ERROR)


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True


print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
print("Starting up")

welcomeMessage = commonTasks.print_to_LCDScreen("Welcome!")
time.sleep(1)
print("Welcome message return status: " + str(welcomeMessage))

screenMessage = commonTasks.get_last_feedtime_string()
print("Screen message to print: " + str(screenMessage))
lastFeedTime = commonTasks.print_to_LCDScreen(screenMessage)
print("Message display return status: " + str(lastFeedTime))

print("Create Gracekiller class")
killer = GracefulKiller()

print("Set up button for While Loop")
sensorButton = int(feedSensorGPIO)
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.cleanup(sensorButton)
GPIO.setup(sensorButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("End Start up. Starting while loop")
print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
while True:
    if GPIO.input(sensorButton) == 0:
        print("-------------------------------------------------------------------------")
        time.sleep(.1)
        buttonPressDatetime = datetime.datetime.now()
        print("Button was pressed at " + str(buttonPressDatetime))

        lastFeedDateCursor = commonTasks.db_get_last_feedtimes(1)
        lastFeedDateString = lastFeedDateCursor[0][0]
        lastFeedDateObject = datetime.datetime.strptime(lastFeedDateString, "%Y-%m-%d %H:%M:%S")
        print("Last feed time in DB was at " + str(lastFeedDateObject))

        tdelta = buttonPressDatetime - lastFeedDateObject
        print("Difference in seconds between two: " + str(tdelta.seconds))

        if tdelta.seconds < int(delayBetweenButtonPushes):
            print("Feed times closure than " + str(delayBetweenButtonPushes) + " seconds. Hold off for now.")
        else:
            dblog = commonTasks.db_insert_feedtime(buttonPressDatetime, 4)
            print("End DB Insert return status: " + str(dblog))
            updatescreen = commonTasks.print_to_LCDScreen(commonTasks.get_last_feedtime_string())
            print("End Message Display return status: " + str(updatescreen))

    if killer.kill_now: break
print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
print("End of the program loop. Killed gracefully")
print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
