#!/var/www/feeder/bin/python
import sys

sys.path.extend(['/var/www/feeder/feeder'])
import subprocess
import sqlite3
import os

from werkzeug.security import generate_password_hash

import datetime

try:
    dbPath = '/var/www/feeder/feeder/feeder.db'
    appCFGPath = '/var/www/feeder/feeder/app.cfg'

    if os.path.isfile(dbPath):
        print('DB já existe. Delete para criar uma cópia atual.')
    else:
        print('Criando DB, Espere.')
        con = sqlite3.connect(dbPath)
        cur = con.execute(
            """CREATE TABLE feedtimes (feedid integer primary key autoincrement,feeddate string,feedtype integer);""")
        cur = con.execute("""CREATE TABLE feedtypes (feedtype integer primary key,description string);""")
        cur = con.execute("""CREATE TABLE balancaFeeds (balancaid integer primary key autoincrement,valorpeso string,estatuspeso string);""") 
        cur = con.execute("""insert into feedtypes (feedtype,description) values ("0","Programado para almientar");""")
        cur = con.execute("""insert into feedtypes (feedtype,description) values ("1","Botão");""")
        cur = con.execute("""insert into feedtypes (feedtype,description) values ("2","WebSite");""")
        cur = con.execute("""insert into feedtypes (feedtype,description) values ("3","Programado");""")
        cur = con.execute("""insert into feedtypes (feedtype,description) values ("4","Sensor do animal");""")
        cur = con.execute("""insert into feedtypes (feedtype,description) values ("5","Progamação diária");""")
        cur = con.execute("""insert into balancaFeeds (valorpeso,estatuspeso) values ("500","Cheio");""")
        nowDate = datetime.datetime.now()
        currentTimeString = nowDate.strftime("%Y-%m-%d %H:%M:%S")
        cur = con.execute('''insert into feedtimes (feeddate,feedtype) values (?,1)''', [currentTimeString, ])
        con.commit()
        cur.close()
        con.close()
        print('DB created')

    if os.path.isfile(appCFGPath):
        print('app.cfg já existe. Delete para criar uma cópia atual.')
    else:
        print('Criando app.cfg. Espere.')
        f = open(appCFGPath, "w+")

        f.write("""[feederConfig]
Database_Location=/var/www/feeder/feeder/feeder.db
Feed_Button_GPIO_Pin=12
Sensor_Button_GPIO=16
Hopper_GPIO_Pin=11
Hopper_Spin_Time=0.6
Log_ButtonService_Filename=/var/www/feeder/feeder/logs/feederButtonService.log
Log_SensorService_Filename=/var/www/feeder/feeder/logs/feederSensorService.log
Log_TimeService_Filename=/var/www/feeder/feeder/logs/feederTimeService.log
Motion_Video_Dir_Path=/var/www/feeder/feeder/static/video
Motion_Camera_Site_Address=http://yourRemoteAddress.duckdns.org:8081
Number_Days_Of_Videos_To_Keep=1
Number_Feed_Times_To_Display=10
Number_Scheduled_Feed_Times_To_Display=7
Number_Videos_To_Display=100
Seconds_Delay_After_Button_Push=3
Seconds_Delay_Between_Schedule_Checks=300
Secretkey=SUPER_SECRET_KEY
""")

        f.close()
        # os.chmod(appCFGPath, 0o777)
        print('app.cfg criado')


    process = subprocess.Popen(["sudo", "chmod", "777", "-R", "/var/www/feeder"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    os.chmod(dbPath, 0o777)
    print('permissions set')

except Exception as e:
    print('Error: ' + str(e))
