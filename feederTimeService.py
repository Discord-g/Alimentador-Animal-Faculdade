#!/var/www/feeder/bin/python
import sys

sys.path.extend(['/var/www/feeder/feeder'])
import logging.handlers
import argparse
import time
import signal
import commonTasks
import configparser
import os
import datetime
from pathlib import Path


dir = os.path.dirname(__file__)  # os.getcwd()
configFilePath = os.path.abspath(os.path.join(dir, "app.cfg"))
configParser = configparser.RawConfigParser()
configParser.read(configFilePath)


secondDelay = configParser.get('feederConfig', 'Seconds_Delay_Between_Schedule_Checks')
LOG_TimeService_FILENAME = configParser.get('feederConfig', 'Log_TimeService_Filename')
hopperGPIO = str(configParser.get('feederConfig', 'Hopper_GPIO_Pin'))
hopperTime = str(configParser.get('feederConfig', 'Hopper_Spin_Time'))
motionVideoDirPath = str(configParser.get('feederConfig', 'Motion_Video_Dir_Path'))
nowMinusXDays = str(configParser.get('feederConfig', 'Number_Days_Of_Videos_To_Keep'))


parser = argparse.ArgumentParser(description="My simple Python service")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_TimeService_FILENAME + "')")


args = parser.parse_args()
if args.log:
    LOG_FILENAME = args.log


logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)

handler = logging.handlers.TimedRotatingFileHandler(LOG_TimeService_FILENAME, when="midnight", backupCount=3)

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
print("Time delay default is: " + str(secondDelay) + " seconds")
print("Create Gracekiller class")
killer = GracefulKiller()
print("End Start up. Starting while loop")
print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
while True:
    print("--------------------------------------------------------------")

    screenMessage = commonTasks.get_last_feedtime_string()

    updatescreen = commonTasks.print_to_LCDScreen(str(screenMessage))



    upcomingXNumberFeedTimes = commonTasks.db_get_scheduled_feedtimes(50)
    for x in upcomingXNumberFeedTimes:
        if str(x[2]) == '5':
            print('Repeating scheduled time ' + str(x[0]))
            present = datetime.datetime.now() 
            preValue = datetime.datetime.strptime(x[0], '%Y-%m-%d %H:%M:%S')

            value = datetime.datetime(present.year, present.month, present.day, preValue.hour, preValue.minute)
            c = present - value
            d = divmod(c.days * 86400 + c.seconds, 60)

            scheduledForToday = commonTasks.db_get_specific_scheduled_feedtime_by_date(value)
            if scheduledForToday:
                print('Already ran for today, skip')
                d = (0, 0)
        else:
            print('One off scheduled time ' + str(x[0]))
            present = datetime.datetime.now()
            value = datetime.datetime.strptime(x[0], '%Y-%m-%d %H:%M:%S')
            c = present - value
            d = divmod(c.days * 86400 + c.seconds, 60)
            if d[0] < 1:
                print('Not past due yet')


        if d[0] > 1:
            print('Scheduled record found past due')
            print("Current time: " + str(present))
            print("Scheduled time: " + str(value))
            print("Minutes difference: " + str(d[0]))

            spin = commonTasks.spin_hopper(hopperGPIO, hopperTime)
            if spin != 'ok':
                print('Error! Feeder not activated! Error Message: ' + str(spin))

            dbInsert = commonTasks.db_insert_feedtime(value, 3)
            if dbInsert != 'ok':
                print('Warning. Database did not update: ' + str(dbInsert))

            updatescreen = commonTasks.print_to_LCDScreen(commonTasks.get_last_feedtime_string())
            if updatescreen != 'ok':
                print('Warning. Screen feedtime did not update: ' + str(updatescreen))

            print('Auto feed success')



            if str(x[2]) == '5':

                print('Scheduled date. Do not delete')

            else:

                con = commonTasks.connect_db()
                cur = con.execute("""delete from feedtimes where feeddate=? and feedtype in (0)""", [str(x[0]), ])
                con.commit()
                cur.close()
                con.close()
                print('Deleted old record from DB')

            break


    now = time.time()
    nowMinusSpecifiedDays = now - int(nowMinusXDays) * 86400

    for f in os.listdir(motionVideoDirPath):
        if f != '.gitkeep':
            f = os.path.join(motionVideoDirPath, f)
            if os.stat(f).st_mtime < nowMinusSpecifiedDays:
                if os.path.isfile(f):
                    os.remove(os.path.join(motionVideoDirPath, f))
                    print('Removed old video file: ' + str(f))

    time.sleep(float(secondDelay))
    if killer.kill_now: break

print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
print("End of the program. Killed gracefully")
print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
