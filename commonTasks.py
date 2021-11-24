import sqlite3
import configparser
import time
from Adafruit_CharLCD import Adafruit_CharLCD
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import *
import RPi.GPIO as GPIO

# Achar arquivo
dir = os.path.dirname(__file__)  # os.getcwd()
configFilePath = os.path.abspath(os.path.join(dir, "app.cfg"))
configParser = configparser.RawConfigParser()
configParser.read(configFilePath)

# Ler as variaves
DB = str(configParser.get('feederConfig', 'Database_Location'))
hopperGPIO = str(configParser.get('feederConfig', 'Hopper_GPIO_Pin'))
hopperTime = str(configParser.get('feederConfig', 'Hopper_Spin_Time'))
latestXNumberFeedTimesValue = str(configParser.get('feederConfig', 'Number_Feed_Times_To_Display'))
upcomingXNumberFeedTimesValue = str(configParser.get('feederConfig', 'Number_Scheduled_Feed_Times_To_Display'))

def connect_db():
    try:
        """Connects to the specific database."""
        rv = sqlite3.connect(DB)
        return rv
    except Exception as e:
        return e


def db_insert_feedtime(dateObject, complete):
    try:
        """Connects to the specific database."""
        datetime = dateObject.strftime('%Y-%m-%d %H:%M:%S')
        con = connect_db()
        cur = con.execute('''insert into feedtimes (feeddate,feedtype) values (?,?)''', [str(datetime), int(complete)])
        con.commit()
        cur.close()
        con.close()

        return 'ok'
    except Exception as e:
        return e


def db_get_last_feedtimes(numberToGet):
    try:
        con = connect_db()
        cur = con.execute(''' select feeddate,description
                                from feedtimes ft
                                join feedtypes fty on ft.feedtype=fty.feedtype
                                where ft.feedtype in (1,2,3)
                                order by feeddate desc
                                limit ?''', [str(numberToGet), ])
        LastFeedingTimes = cur.fetchall()
        cur.close()
        con.close()
        return LastFeedingTimes
    except Exception as e:
        return e
    
def db_get_last_sensortimes(numberToGet):
    try:
        con = connect_db()
        cur = con.execute(''' select feeddate,description
                                from feedtimes ft
                                join feedtypes fty on ft.feedtype=fty.feedtype
                                where ft.feedtype in (4)
                                order by feeddate desc
                                limit ?''', [str(numberToGet), ])
        LastFeedingTimes = cur.fetchall()
        cur.close()
        con.close()
        return LastFeedingTimes
    except Exception as e:
        return e


def db_get_scheduled_feedtimes(numberToGet):
    try:
        con = connect_db()
        cur = con.execute(''' select feeddate,description,ft.feedtype
                                from feedtimes ft
                                join feedtypes fty on ft.feedtype=fty.feedtype
                                where ft.feedtype in (0,5)
                                order by ft.feedtype desc,ft.feeddate desc
                            limit ?''', [str(numberToGet), ])
        LastFeedingTimes = cur.fetchall()
        cur.close()
        con.close()
        return LastFeedingTimes
    except Exception as e:
        return e


def db_get_specific_scheduled_feedtime_by_date(date):
    try:
        con = connect_db()
        cur = con.execute(''' select feedid, feeddate, feedtype
                                from feedtimes ft
                                where feedtype in (3)
                                and feeddate=?
                            ''', [str(date), ])
        LastFeedingTimes = cur.fetchone()
        cur.close()
        con.close()
        return LastFeedingTimes
    except Exception as e:
        return e


def get_last_feedtime_string():
    try:
        # Get last date from database
        lastFeedDateCursor = db_get_last_feedtimes(1)
        lastFeedDateString = lastFeedDateCursor[0][0]
        lastFeedDateObject = datetime.datetime.strptime(lastFeedDateString, "%Y-%m-%d %H:%M:%S")

        yesterdayDateObject = datetime.datetime.now() - datetime.timedelta(days=1)
        nowDateObject = datetime.datetime.now()
        verbiageString = ''
        finalMessage = ''
        if lastFeedDateObject.year == nowDateObject.year and lastFeedDateObject.month == nowDateObject.month and lastFeedDateObject.day == nowDateObject.day:
            verbiageString = 'Today' + ' ' + lastFeedDateObject.strftime(
                "%I:%M %p")  # +str('%02d' % lastFeedDateObject.hour)+':'+str('%02d' % lastFeedDateObject.minute)
        elif lastFeedDateObject.year == yesterdayDateObject.year and lastFeedDateObject.month == yesterdayDateObject.month and lastFeedDateObject.day == yesterdayDateObject.day:
            verbiageString = 'Yesterday' + ' ' + lastFeedDateObject.strftime("%I:%M %p").replace(' ',
                                                                                                 '')  # str('%02d' % lastFeedDateObject.hour)+':'+str('%02d' % lastFeedDateObject.minute)
        else:
            verbiageString = str(abs((
                                             nowDateObject - lastFeedDateObject).days)) + ' days ago!'  # str('%02d' % lastFeedDateObject.month)+'-'+str('%02d' % lastFeedDateObject.day)+'-'+str(lastFeedDateObject.year)[2:]+' '+str('%02d' % lastFeedDateObject.hour)+':'+str('%02d' % lastFeedDateObject.minute)

        finalMessage = 'Ultimo feed:\n' + verbiageString
        return finalMessage
    except Exception as e:
        return e
    
def get_last_sensortime_string():
    try:
        # Get last date from database
        lastFeedDateCursor = db_get_last_sensortimes(1)
        lastFeedDateString = lastFeedDateCursor[0][0]
        lastFeedDateObject = datetime.datetime.strptime(lastFeedDateString, "%Y-%m-%d %H:%M:%S")

        yesterdayDateObject = datetime.datetime.now() - datetime.timedelta(days=1)
        nowDateObject = datetime.datetime.now()
        verbiageString = ''
        finalMessage = ''
        if lastFeedDateObject.year == nowDateObject.year and lastFeedDateObject.month == nowDateObject.month and lastFeedDateObject.day == nowDateObject.day:
            verbiageString = 'Today' + ' ' + lastFeedDateObject.strftime(
                "%I:%M %p")  # +str('%02d' % lastFeedDateObject.hour)+':'+str('%02d' % lastFeedDateObject.minute)
        elif lastFeedDateObject.year == yesterdayDateObject.year and lastFeedDateObject.month == yesterdayDateObject.month and lastFeedDateObject.day == yesterdayDateObject.day:
            verbiageString = 'Yesterday' + ' ' + lastFeedDateObject.strftime("%I:%M %p").replace(' ',
                                                                                                 '')  # str('%02d' % lastFeedDateObject.hour)+':'+str('%02d' % lastFeedDateObject.minute)
        else:
            verbiageString = str(abs((
                                             nowDateObject - lastFeedDateObject).days)) + ' days ago!'  # str('%02d' % lastFeedDateObject.month)+'-'+str('%02d' % lastFeedDateObject.day)+'-'+str(lastFeedDateObject.year)[2:]+' '+str('%02d' % lastFeedDateObject.hour)+':'+str('%02d' % lastFeedDateObject.minute)

        finalMessage = 'Sensor acionado:\n' + verbiageString
        return finalMessage
    except Exception as e:
        return e


def spin_hopper(pin, duration):
    try:
        pin = int(pin)
        duration = float(duration)
        GPIO.setwarnings(False)
        GPIO.cleanup(pin)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(duration)
        GPIO.output(pin, GPIO.HIGH)
        GPIO.cleanup(pin)

        atualiza_balanca(1)

        return 'ok'
    except Exception as e:
        return 'ok'  # e


def atualiza_balanca(numberToGet):
    try:
        con = connect_db()
        cur = con.execute(''' select valorpeso,estatuspeso
                                from balancaFeeds ft
                                order by balancaid desc
                                limit ?''', [str(numberToGet), ])
        UltimoPeso = cur.fetchone()
        UltimoPeso = list(UltimoPeso)
        PesoAtual = int(UltimoPeso[0])
        PesoAtual = PesoAtual-5
        Descricao = ''
        if PesoAtual >= 300:
            Descricao = 'Cheio'
        elif PesoAtual < 300 and PesoAtual >= 100:
            Descricao = 'Meio Cheio'
        elif PesoAtual < 100 and PesoAtual > 0:
            Descricao = 'Meio Vazio'
        else:
            PesoAtual = 0
            Descricao = 'Vazio'
        cur.close()
        con.close()
        Insert_Peso(PesoAtual, Descricao)
        return 'ok'
    except Exception as e:
        return 'ok'

def Insert_Peso(peso, desc):
    try:
        """Connects to the specific database."""
        con = connect_db()
        cur = con.execute('''insert into balancaFeeds (valorpeso,estatuspeso) values (?,?)''', [str(peso), desc])
        con.commit()
        cur.close()
        con.close()

        return 'ok'
    except Exception as e:
        return e

def Get_Last_Peso(numberToGet):
    try:
        con = connect_db()
        cur = con.execute(''' select valorpeso,
                                from balancaFeeds ft
                                order by balancaid desc
                                limit ?''', [str(numberToGet), ])
        LastFeedingTimes = cur.fetchall()
        cur.close()
        con.close()
        return LastFeedingTimes
    except Exception as e:
        return e

def print_to_LCDScreen(message):
    try:
        lcd = Adafruit_CharLCD()
        lcd.begin(16, 2)
        for x in range(0, 16):
            for y in range(0, 2):
                lcd.setCursor(x, y)
                lcd.message('>')
                time.sleep(.025)
        lcd.noDisplay()
        lcd.clear()
        lcd.message(str(message))
        for x in range(0, 16):
            lcd.DisplayLeft()
        lcd.display()
        for x in range(0, 16):
            lcd.scrollDisplayRight()
            time.sleep(.05)

        return 'ok'
    except Exception as e:
        return 'ok'  # e
