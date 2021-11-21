#!/home/pi/venv/feeder/bin/python
from __future__ import with_statement
import sys

sys.path.extend(['/var/www/feeder/feeder/logs'])
import sqlite3
from flask import Flask, flash, Markup, redirect, render_template, request, Response, session, url_for, abort
import subprocess
import commonTasks
import os
import configparser
import datetime

from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from stat import S_ISREG, ST_CTIME, ST_MODE
import os, sys, time

app = Flask(__name__)

# Achar arquivo
# dir = os.path.dirname(__file__)  # os.getcwd()
# configFilePath = os.path.abspath(os.path.join(dir, "app.cfg"))
configParser = configparser.RawConfigParser()
configParser.read('/var/www/feeder/feeder/app.cfg')

#Variaveis dos arquivos
SECRETKEY = str(configParser.get('feederConfig', 'Secretkey'))
hopperGPIO = str(configParser.get('feederConfig', 'Hopper_GPIO_Pin'))
hopperTime = str(configParser.get('feederConfig', 'Hopper_Spin_Time'))
DB = str(configParser.get('feederConfig', 'Database_Location'))
latestXNumberFeedTimesValue = str(configParser.get('feederConfig', 'Number_Feed_Times_To_Display'))
upcomingXNumberFeedTimesValue = str(configParser.get('feederConfig', 'Number_Scheduled_Feed_Times_To_Display'))
motionVideoDirPath = str(configParser.get('feederConfig', 'Motion_Video_Dir_Path'))
latestXNumberVideoFeedTimesValue = str(configParser.get('feederConfig', 'Number_Videos_To_Display'))
motionCameraSiteAddress = str(configParser.get('feederConfig', 'Motion_Camera_Site_Address'))
nowMinusXDays = str(configParser.get('feederConfig', 'Number_Days_Of_Videos_To_Keep'))


#####################################################################################
##########################################HOME PAGE##################################
#####################################################################################
@app.route('/', methods=['GET', 'POST'])
def home_page():
    try:

        latestXNumberFeedTimes = commonTasks.db_get_last_feedtimes(latestXNumberFeedTimesValue)

        upcomingXNumberFeedTimes = commonTasks.db_get_scheduled_feedtimes(upcomingXNumberFeedTimesValue)

        latestPeso = commonTasks.Get_Last_Peso(1)

        finalFeedTimeList = []
        for x in latestXNumberFeedTimes:
            x = list(x)
            dateobject = datetime.datetime.strptime(x[0], '%Y-%m-%d %H:%M:%S')
            x[0] = dateobject.strftime("%m-%d-%y %I:%M %p")
            x = tuple(x)
            finalFeedTimeList.append(x)

        finalUpcomingFeedTimeList = []
        for x in upcomingXNumberFeedTimes:
            x = list(x)
            dateobject = datetime.datetime.strptime(x[0], '%Y-%m-%d %H:%M:%S')
            finalString = dateobject.strftime("%m-%d-%y %I:%M %p")

            # 1900-01-01 default 
            if str(x[2]) == '5':  # Repetição dos horários
                finalString = finalString.replace("01-01-00", "Diario em")

            finalUpcomingFeedTimeList.append(finalString)

        finalPeso = []
        for x in latestPeso:
            x = list(x)
            finalPeso.append(x)

        # latestXVideoFeedTimes
        latestXVideoFeedTimes = []
        for path, subdirs, files in os.walk(motionVideoDirPath):
            for name in sorted(files, key=lambda name:
            os.path.getmtime(os.path.join(path, name))):
                if name.endswith('.mkv'):
                    vidDisplayDate = datetime.datetime.fromtimestamp(
                        os.path.getmtime(os.path.join(path, name))).strftime('%m-%d-%y %I:%M %p')
                    vidFileName = name
                    vidFileSize = str(round(os.path.getsize(os.path.join(path, name)) / (1024 * 1024.0), 1))
                    latestXVideoFeedTimes.append([vidDisplayDate, vidFileName, vidFileSize])

        latestXVideoFeedTimes = latestXVideoFeedTimes[::-1]  # Inverte para o mais novo ser o primeiro
        latestXVideoFeedTimes = latestXVideoFeedTimes[:int(latestXNumberVideoFeedTimesValue)]

        

        cameraStatusOutput = DetectCamera()

        # cameraStatusOutput = 'supported=0 detected=1'
        if "detected=1" in str(cameraStatusOutput):
            cameraStatus = '1'
        else:
            cameraStatus = '0'

        # Volta pra home
        return render_template('home.html', latestXNumberFeedTimes=finalFeedTimeList
                               , upcomingXNumberFeedTimes=finalUpcomingFeedTimeList
                               , latestPeso=finalPeso
                               , cameraSiteAddress=motionCameraSiteAddress
                               , latestXVideoFeedTimes=latestXVideoFeedTimes
                               , cameraStatus=cameraStatus
                               )

    except Exception as e:
        return render_template('home.html', resultsSET=e)


@app.route('/feedbuttonclick', methods=['GET', 'POST'])
def feedbuttonclick():
    try:
        dateNowObject = datetime.datetime.now()

        spin = commonTasks.spin_hopper(hopperGPIO, hopperTime)

        if spin != 'ok':
            flash('Error! No feed activated! Error Message: ' + str(spin), 'error')
            return redirect(url_for('home_page'))

        dbInsert = commonTasks.db_insert_feedtime(dateNowObject, 2)  # FeedType 2=Button Click
        if dbInsert != 'ok':
            flash('Warning. Database did not update: ' + str(dbInsert), 'warning')
            return redirect(url_for('home_page'))

        updatescreen = commonTasks.print_to_LCDScreen(commonTasks.get_last_feedtime_string())
        if updatescreen != 'ok':
            flash('Warning. Screen feedtime did not update: ' + str(updatescreen), 'warning')
            return redirect(url_for('home_page'))

        flash('Feed success!')
        return redirect(url_for('home_page'))
    except Exception as e:
        return render_template('home.html', resultsSET=e)

@app.route('/scheduleDatetime', methods=['GET', 'POST'])
def scheduleDatetime():
    try:
        scheduleDatetime = [request.form['scheduleDatetime']][0]
        scheduleTime = [request.form['scheduleTime']][0]

        dateobj = datetime.datetime.strptime(scheduleDatetime, '%Y-%m-%d')
        timeobj = datetime.datetime.strptime(scheduleTime, '%H:%M').time()

        dateobject = datetime.datetime.combine(dateobj, timeobj)

        dbInsert = commonTasks.db_insert_feedtime(dateobject, 0)  # FeedType 0=One Time Scheduled Feed
        if dbInsert != 'ok':
            flash('Error! The time has not been scheduled! Error Message: ' + str(dbInsert), 'error')
            return redirect(url_for('home_page'))

        flash("Time Scheduled")
        return redirect(url_for('home_page'))
    except Exception as e:
        return render_template('home.html', resultsSET=e)


@app.route('/scheduleRepeatingDatetime', methods=['GET', 'POST'])
def scheduleRepeatingDatetime():
    try:
        scheduleRepeatingTime = [request.form['scheduleRepeatingTime']][0]
        timeobj = datetime.datetime.strptime(scheduleRepeatingTime, '%H:%M').time()

        dbInsert = commonTasks.db_insert_feedtime(timeobj, 5)  # FeedType 5=Repeat Daily Scheduled Feed
        if dbInsert != 'ok':
            flash('Error! The time has not been scheduled! Error Message: ' + str(dbInsert), 'error')
            return redirect(url_for('home_page'))

        flash("Time Scheduled")
        return redirect(url_for('home_page'))
    except Exception as e:
        return render_template('home.html', resultsSET=e)

#deleta no site e no DB
@app.route('/deleteRow/<history>', methods=['GET', 'POST'])
def deleteRow(history):
    try:
        if "Diario em" in history:
            history = history.replace("Diario em", "01-01-1900")
            dateObj = datetime.datetime.strptime(history, "%m-%d-%Y %I:%M %p")
        else:
            dateObj = datetime.datetime.strptime(history, "%m-%d-%y %I:%M %p")

        deleteRowFromDB = deleteUpcomingFeedingTime(str(dateObj))
        if deleteRowFromDB != 'ok':
            flash('Error! The row has not been deleted! Error Message: ' + str(deleteRowFromDB), 'error')
            return redirect(url_for('home_page'))

        flash("Scheduled time deleted")
        return redirect(url_for('home_page'))

    except Exception as e:
        return render_template('home.html', resultsSET=e)


def deleteUpcomingFeedingTime(dateToDate):
    try:
        con = commonTasks.connect_db()
        cur = con.execute("""delete from feedtimes where feeddate=?""", [str(dateToDate), ])
        con.commit()
        cur.close()
        con.close()
        return 'ok'
    except Exception as e:
        return e

#funções para video
@app.route('/video/<videoid>', methods=['GET', 'POST'])
def video_page(videoid):
    try:
        valid = 0

        for f in os.listdir(motionVideoDirPath):
            if f == videoid:
                valid = 1

        if valid == 1:
            return render_template('camera.html', videoid=videoid)
        else:
            abort(404)
    except Exception as e:
        return render_template('camera.html', resultsSET=e)


def DetectCamera():
    try:

        process = subprocess.Popen(["vcgencmd", "get_camera"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        return process.stdout.read()
    except Exception as e:
        return 'status=0'

app.secret_key = SECRETKEY

# main
if __name__ == '__main__':
    app.debug = False  # reload on code changes. show traceback
    app.run(host='0.0.0.0', threaded=True)
