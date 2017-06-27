import os
import re
import sys
import time
import thread
import sqlite3
import commands
import subprocess

import variables
from PyQt4 import QtGui,QtCore

from wep import *
from wpa import *
from wps import *
from tools import *
from database import *
from variables import *
from functions import *
from settings import *

from gui.main_window import *

__version__= 2.4

#
# Main Window Class
#
class mainwindow(QtGui.QDialog,Ui_Dialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.retranslateUi(self)
        self.refresh_interface()
        self.evaliate_permissions()

        self.monitor_interface = str()
        self.wep_count = str()
        self.wpa_count = str()

        self.interface_cards = list()

        variables.wps_functions = WPS_Attack()          # WPS functions

        self.movie = QtGui.QMovie(self)
        self.animate_monitor_mode(True)                 # Loading gif animation

        self.settings = Fern_settings()

        self.timer = QtCore.QTimer()
        self.connect(self.timer,QtCore.SIGNAL("timeout()"),self.display_timed_objects)
        self.timer.setInterval(4000)
        self.timer.start()

        self.connect(self,QtCore.SIGNAL("DoubleClicked()"),self.mouseDoubleClickEvent)
        self.connect(self.refresh_intfacebutton,QtCore.SIGNAL("clicked()"),self.refresh_interface)
        self.connect(self.interface_combo,QtCore.SIGNAL("currentIndexChanged(QString)"),self.setmonitor)
        self.connect(self,QtCore.SIGNAL("monitor mode enabled"),self.monitor_mode_enabled)
        self.connect(self,QtCore.SIGNAL("monitor_failed()"),self.display_error_monitor)
        self.connect(self,QtCore.SIGNAL("interface cards found"),self.interface_cards_found)
        self.connect(self,QtCore.SIGNAL("interface cards not found"),self.interface_card_not_found)
        self.connect(self.scan_button,QtCore.SIGNAL("clicked()"),self.scan_network)
        self.connect(self.wep_button,QtCore.SIGNAL("clicked()"),self.wep_attack_window)
        self.connect(self.wpa_button,QtCore.SIGNAL("clicked()"),self.wpa_attack_window)
        self.connect(self.attack_options_button,QtCore.SIGNAL("clicked()"),self.attack_settings_exec)

        self.connect(self,QtCore.SIGNAL("wep_number_changed"),self.wep_number_changed)
        self.connect(self,QtCore.SIGNAL("wep_button_true"),self.wep_button_true)
        self.connect(self,QtCore.SIGNAL("wep_button_false"),self.wep_button_false)

        self.connect(self,QtCore.SIGNAL("wpa_number_changed"),self.wpa_number_changed)
        self.connect(self,QtCore.SIGNAL("wpa_button_true"),self.wpa_button_true)
        self.connect(self,QtCore.SIGNAL("wpa_button_false"),self.wpa_button_false)

        self.connect(self.database_button,QtCore.SIGNAL("clicked()"),self.database_window)
        self.connect(self,QtCore.SIGNAL('internal scan error'),self.scan_error_display)

        self.set_WindowFlags()

        self.update_database_label()
        self.set_xterm_settings()


    def set_WindowFlags(self):
        try:
            self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMaximizeButtonHint)       # Some older versions of Qt4 dont support some flags
        except:pass


    def display_timed_objects(self):
        self.timer.stop()


    #
    #   Read database entries and count entries then set Label on main window
    #
    def update_database_label(self):
        connection = sqlite3.connect(os.getcwd() + '/key-database/Database.db')
        query = connection.cursor()
        query.execute('''select * from keys''')
        items = query.fetchall()
        connection.close()
        if len(items) == 0:
            self.label_16.setText(QtGui.QApplication.translate("more", "<font color=red>No Key Entries</font>", None, QtGui.QApplication.UnicodeUTF8))
        else:
            self.label_16.setText(QtGui.QApplication.translate("more", '<font color=green>%s Key Entries</font>', None, QtGui.QApplication.UnicodeUTF8) %(str(len(items))))


    #
    #   Read last xterm settings
    #
    def set_xterm_settings(self):
        if not self.settings.setting_exists("xterm"):
            self.settings.create_settings("xterm",str())
        variables.xterm_setting = self.settings.read_last_settings("xterm")


    def percentage(self,current,total):
        float_point = float(current)/float(total)
        calculation = int(float_point * 100)
        percent = str(calculation) + '%'
        return(percent)


    def attack_settings_exec(self):
        wifi_attack_settings_box = wifi_attack_settings()
        wifi_attack_settings_box.exec_()
    #
    # Execute the wep attack window
    #
    def wep_attack_window(self):
        if 'WEP-DUMP' not in os.listdir('/tmp/fern-log'):
            os.mkdir('/tmp/fern-log/WEP-DUMP',0700)
        else:
            variables.exec_command('rm -r /tmp/fern-log/WEP-DUMP/*')
        wep_run = wep_attack_dialog()

        self.connect(wep_run,QtCore.SIGNAL('update database label'),self.update_database_label)
        self.connect(wep_run,QtCore.SIGNAL("stop scan"),self.stop_network_scan)

        wep_run.exec_()

    #
    # Execute the wep attack window
    #
    def wpa_attack_window(self):
        variables.exec_command('killall aircrack-ng')
        if 'WPA-DUMP' not in os.listdir('/tmp/fern-log'):
            os.mkdir('/tmp/fern-log/WPA-DUMP',0700)
        else:
            variables.exec_command('rm -r /tmp/fern-log/WPA-DUMP/*')
        wpa_run = wpa_attack_dialog()

        self.connect(wpa_run,QtCore.SIGNAL('update database label'),self.update_database_label)
        self.connect(wpa_run,QtCore.SIGNAL("stop scan"),self.stop_network_scan)

        wpa_run.exec_()
    #
    # Execute database Window
    #
    def database_window(self):
        database_run = database_dialog()
        self.connect(database_run,QtCore.SIGNAL('update database label'),self.update_database_label)
        database_run.exec_()
    #
    # Refresh wireless network interface card and update combobo
    #

    def refresh_interface(self):
        variables.exec_command('killall airodump-ng')
        variables.exec_command('killall airmon-ng')

        self.animate_monitor_mode(True)
        self.mon_label.clear()
        self.interface_combo.clear()
        self.interface_combo.setEnabled(True)
        self.interface_cards = list()

        thread.start_new_thread(self.refresh_card_thread,())


    def refresh_card_thread(self):
        # Disable cards already on monitor modes
        wireless_interfaces = str(commands.getstatusoutput('airmon-ng'))
        prev_monitor = os.listdir('/sys/class/net')
        monitor_interfaces_list = []
        for monitors in prev_monitor:
            if monitors in wireless_interfaces:
                monitor_interfaces_list.append(monitors)
        for monitored_interfaces in monitor_interfaces_list:
            variables.exec_command('airmon-ng stop %s'%(monitored_interfaces))

        # List Interface cards
        compatible_interface = str(commands.getoutput("airmon-ng | egrep -e '^[a-z]{2,4}[0-9]'"))
        interface_list = os.listdir('/sys/class/net')
        # Interate over interface output and update combo box
        if compatible_interface.count('\t') == 0:
            self.emit(QtCore.SIGNAL("interface cards not found"))
        else:
            for interface in interface_list:
                if interface in compatible_interface:
                    if not interface.startswith('mon'):
                        self.interface_cards.append(interface)

            self.emit(QtCore.SIGNAL("interface cards found"))



    def interface_card_not_found(self):
        self.interface_combo.setEnabled(False)
        self.mon_label.setText(QtGui.QApplication.translate("more", "<font color=red>No Wireless Interface was found</font>", None, QtGui.QApplication.UnicodeUTF8))
        self.animate_monitor_mode(False)


    def interface_cards_found(self):
        self.interface_combo.addItem('Select Interface')
        interface_icon = QtGui.QIcon("%s/resources/mac_address.png"%(os.getcwd()))
        for interface in self.interface_cards:
            self.interface_combo.addItem(interface_icon,interface)
        self.mon_label.setText(QtGui.QApplication.translate("more", "<font color=red>Select an interface card</font>", None, QtGui.QApplication.UnicodeUTF8))
        self.animate_monitor_mode(False)


    #
    # Animates monitor mode by loading gif
    #
    def animate_monitor_mode(self,status):
        self.movie = QtGui.QMovie("%s/resources/loading.gif"%(os.getcwd()))
        self.movie.start()
        self.loading_label.setMovie(self.movie)

        if(status):      # if status == True (setting of monitor mode is in progress)
            self.interface_combo.setEnabled(False)
            self.loading_label.setVisible(True)
            self.mon_label.setVisible(False)
        else:
            self.interface_combo.setEnabled(True)
            self.loading_label.setVisible(False)
            self.mon_label.setVisible(True)


    #
    # Set monitor mode on selected monitor from combo list
    #
    def setmonitor(self):
        last_settings = str()
        self.monitor_interface = str()
        monitor_card = str(self.interface_combo.currentText())
        if monitor_card != 'Select Interface':
            mac_settings = self.settings.setting_exists('mac_address')
            if(mac_settings):
                last_settings = self.settings.read_last_settings('mac_address')
            thread.start_new_thread(self.set_monitor_thread,(monitor_card,mac_settings,last_settings,))
            self.animate_monitor_mode(True)
        else:
            self.mon_label.setText(QtGui.QApplication.translate("more", "<font color=red>Monitor Mode not enabled check manually</font>", None, QtGui.QApplication.UnicodeUTF8))
            self.animate_monitor_mode(False)


    def killConflictProcesses(self):
        process = commands.getstatusoutput("airmon-ng check")
        status = process[0]
        output = process[1]

        if(status == 0):
            for line in output.splitlines():
                splitedLines = line.split()
                if(len(splitedLines) >= 2):
                    prefix = str(splitedLines[0])
                    if(prefix.isdigit()):
                        pid = int(prefix)
                        killProcess(pid)



    def set_monitor_thread(self,monitor_card,mac_setting_exists,last_settings):
        self.killConflictProcesses()

        commands.getstatusoutput('ifconfig %s down'%(self.monitor_interface))       # Avoid this:  "ioctl(SIOCSIWMODE) failed: Device or resource busy"

        status = str(commands.getoutput("airmon-ng start %s"%(monitor_card)))
        messages = ("monitor mode enabled","monitor mode vif enabled","monitor mode already")

        monitor_created = False;

        for x in messages:
            if(x in status):
                monitor_created = True


        if (monitor_created):
            monitor_interface_process = str(commands.getoutput("airmon-ng"))

            regex = object()
            if ('monitor mode enabled' in status):
                regex = re.compile("mon\d",re.IGNORECASE)

            elif ('monitor mode vif enabled' in status):
                regex = re.compile("wlan\dmon",re.IGNORECASE)

            interfaces = regex.findall(monitor_interface_process)
            if(interfaces):
                self.monitor_interface = interfaces[0]
            else:
                self.monitor_interface = monitor_card

            variables.monitor_interface = self.monitor_interface
            self.interface_combo.setEnabled(False)
            variables.wps_functions.monitor_interface = self.monitor_interface
            self.emit(QtCore.SIGNAL("monitor mode enabled"))

            # Create Fake Mac Address and index for use
            mon_down = commands.getstatusoutput('ifconfig %s down'%(self.monitor_interface))
            if mac_setting_exists:
                variables.exec_command('macchanger -m %s %s'%(last_settings,self.monitor_interface))
            else:
                variables.exec_command('macchanger -A %s'%(self.monitor_interface))
            #mon_up = commands.getstatusoutput('ifconfig %s up'%(self.monitor_interface))       # Lets leave interface down to avoid channel looping during channel specific attack

            commands.getstatusoutput('ifconfig %s down'%(self.monitor_interface))

            for iterate in os.listdir('/sys/class/net'):
                if str(iterate) == str(self.monitor_interface):
                    os.chmod('/sys/class/net/' + self.monitor_interface + '/address',0777)
                    variables.monitor_mac_address = reader('/sys/class/net/' + self.monitor_interface + '/address').strip()
                    variables.wps_functions.monitor_mac_address = variables.monitor_mac_address
        else:
            self.emit(QtCore.SIGNAL("monitor_failed()"))



    def display_monitor_error(self,color,error):
        message = "<font color='"+color+"'>"+error+"</font>"
        self.mon_label.setText(message)
        self.animate_monitor_mode(False)


    def tip_display(self):
        tips = tips_window()
        tips.type = 1
        tips.exec_()


    def display_error_monitor(self):
        self.display_monitor_error("red",QtGui.QApplication.translate("more", "problem occured while setting up the monitor mode of selected", None, QtGui.QApplication.UnicodeUTF8))


    def monitor_mode_enabled(self):
        self.mon_label.setText(QtGui.QApplication.translate("more", "<font color=green>Monitor Mode Enabled on %s</font>"%(self.monitor_interface), None, QtGui.QApplication.UnicodeUTF8))
        self.animate_monitor_mode(False)
        # Execute tips
        if(self.settings.setting_exists("tips")):
            if(self.settings.read_last_settings("tips") == "0"):
                self.tip_display()
        else:
            self.settings.create_settings("tips","1")
            self.tip_display()


    #
    # Double click event for poping of settings dialog box
    #
    def mouseDoubleClickEvent(self, event):
        if(len(self.monitor_interface)):
            setting = settings_dialog()
            setting.exec_()
        else:
            self.mon_label.setText(QtGui.QApplication.translate("more", "<font color=red>Enable monitor mode to access settings</font>", None, QtGui.QApplication.UnicodeUTF8) )


    def scan_error_display(self):
        global error_catch
        self.stop_scan_network()
        QtGui.QMessageBox.warning(self,'Scan Error',QtGui.QApplication.translate("more", 'Fern failed to start scan due to an airodump-ng error: <font color=red>' + error_catch[1] + '</font>', None, QtGui.QApplication.UnicodeUTF8) )



    #
    # Scan for available networks
    #
    def scan_network(self):
        global scan_control
        scan_control = 0

        self.wep_count = int()
        self.wpa_count = int()

        variables.wep_details = {}
        variables.wpa_details = {}

        variables.wps_functions = WPS_Attack()                      # WPS functions

        variables.wps_functions.monitor_interface = self.monitor_interface
        variables.wps_functions.monitor_mac_address = variables.monitor_mac_address

        variables.wps_functions.start_WPS_Devices_Scan()            # Starts WPS Scanning

        if not self.monitor_interface:
            self.mon_label.setText(QtGui.QApplication.translate("more", "<font color=red>Enable monitor mode before scanning</font>", None, QtGui.QApplication.UnicodeUTF8))
        else:
            self.wpa_button.setEnabled(False)
            self.wep_button.setEnabled(False)
            self.wep_clientlabel.setEnabled(False)
            self.wpa_clientlabel.setEnabled(False)
            self.wep_clientlabel.setText(QtGui.QApplication.translate("more", "None Detected", None, QtGui.QApplication.UnicodeUTF8))
            self.wpa_clientlabel.setText(QtGui.QApplication.translate("more", "None Detected", None, QtGui.QApplication.UnicodeUTF8))
            self.label_7.setText(QtGui.QApplication.translate("more", "<font Color=green>\t Initializing</font>", None, QtGui.QApplication.UnicodeUTF8))
            thread.start_new_thread(self.scan_wep,())
            self.disconnect(self.scan_button,QtCore.SIGNAL("clicked()"),self.scan_network)
            self.connect(self.scan_button,QtCore.SIGNAL("clicked()"),self.stop_scan_network)



    def stop_scan_network(self):
        global error_catch
        global scan_control
        scan_control = 1
        variables.exec_command('rm -r /tmp/fern-log/*.cap')
        variables.exec_command('killall airodump-ng')
        variables.exec_command('killall airmon-ng')
        self.label_7.setText(QtGui.QApplication.translate("more", "<font Color=red>\t Stopped</font>", None, QtGui.QApplication.UnicodeUTF8))
        variables.wps_functions.stop_WPS_Scanning()                 # Stops WPS scanning
        self.wep_clientlabel.setText(QtGui.QApplication.translate("more", "None Detected", None, QtGui.QApplication.UnicodeUTF8))
        self.wpa_clientlabel.setText(QtGui.QApplication.translate("more", "None Detected", None, QtGui.QApplication.UnicodeUTF8))
        self.disconnect(self.scan_button,QtCore.SIGNAL("clicked()"),self.stop_scan_network)
        self.connect(self.scan_button,QtCore.SIGNAL("clicked()"),self.scan_network)



    def stop_network_scan(self):
        global scan_control
        scan_control = 1
        variables.exec_command('killall airodump-ng')
        variables.exec_command('killall airmon-ng')
        self.label_7.setText(QtGui.QApplication.translate("more", "<font Color=red>\t Stopped</font>", None, QtGui.QApplication.UnicodeUTF8))

    #
    # WEP Thread SLOTS AND SIGNALS
    #
    def wep_number_changed(self):
        self.wep_clientlabel.setText(QtGui.QApplication.translate("more", '<font color=red>%s</font><font color=red>\t Detected</font>'%(self.wep_count), None, QtGui.QApplication.UnicodeUTF8))

    def wep_button_true(self):
        self.wep_button.setEnabled(True)
        self.wep_clientlabel.setEnabled(True)

    def wep_button_false(self):
        self.wep_button.setEnabled(False)
        self.wep_clientlabel.setEnabled(False)
        self.wep_clientlabel.setText(QtGui.QApplication.translate("more", 'None Detected', None, QtGui.QApplication.UnicodeUTF8))
    #
    # WPA Thread SLOTS AND SIGNALS
    #
    def wpa_number_changed(self):
        self.wpa_clientlabel.setText(QtGui.QApplication.translate("more", '<font color=red>%s</font><font color=red>\t Detected</font>'%(self.wpa_count), None, QtGui.QApplication.UnicodeUTF8))

    def wpa_button_true(self):
        self.wpa_button.setEnabled(True)
        self.wpa_clientlabel.setEnabled(True)

    def wpa_button_false(self):
        self.wpa_button.setEnabled(False)
        self.wpa_clientlabel.setEnabled(False)
        self.wpa_clientlabel.setText(QtGui.QApplication.translate("more", 'None Detected', None, QtGui.QApplication.UnicodeUTF8))

    #
    # WEP SCAN THREADING FOR AUTOMATIC SCAN OF NETWORK
    #
    ###################
    def scan_process1_thread(self):
        global error_catch
        error_catch = variables.exec_command("airodump-ng --write /tmp/fern-log/zfern-wep --output-format csv \
                                    --encrypt wep %s"%(self.monitor_interface))          #FOR WEP

    def scan_process1_thread1(self):
        global error_catch
        error_catch = variables.exec_command("airodump-ng --write /tmp/fern-log/WPA/zfern-wpa --output-format csv \
                                    --encrypt wpa %s"%(self.monitor_interface))      # FOR WPA

    ###################
    def scan_process2_thread(self):
        global error_catch
        if bool(variables.xterm_setting):
            wep_display_mode = 'xterm -T "FERN (WEP SCAN)" -geometry 100 -e'       # if True or if xterm contains valid ascii characters
        else:
            wep_display_mode = ''

        error_catch = variables.exec_command("%s 'airodump-ng -a --write /tmp/fern-log/zfern-wep --output-format csv\
                                        --encrypt wep %s'"%(wep_display_mode,self.monitor_interface))      #FOR WEP



    def scan_process2_thread1(self):
        global error_catch
        if bool(variables.xterm_setting):                                             # if True or if xterm contains valid ascii characters
            wpa_display_mode = 'xterm -T "FERN (WPA SCAN)" -geometry 100 -e'
        else:
            wpa_display_mode = ''

        error_catch = variables.exec_command("%s 'airodump-ng -a --write /tmp/fern-log/WPA/zfern-wpa \
                                    --output-format csv  --encrypt wpa %s'"%(wpa_display_mode,self.monitor_interface))  # FOR WPA



    ###########################
    def scan_process3_thread(self):
        global error_catch
        error_catch = variables.exec_command("airodump-ng --channel %s --write /tmp/fern-log/zfern-wep \
                                    --output-format csv  --encrypt wep %s"%(variables.static_channel,self.monitor_interface))    #FOR WEP



    def scan_process3_thread1(self):
        global error_catch
        error_catch = variables.exec_command("airodump-ng --channel %s --write /tmp/fern-log/WPA/zfern-wpa \
                                --output-format csv  --encrypt wpa %s"%(variables.static_channel,self.monitor_interface))# FOR WPA


    #######################
    def scan_process4_thread(self):
        global error_catch
        if bool(variables.xterm_setting):
            wep_display_mode = 'xterm -T "FERN (WEP SCAN)" -geometry 100 -e'       # if True or if xterm contains valid ascii characters
        else:
            wep_display_mode = ''

        error_catch = variables.exec_command("%s 'airodump-ng -a --channel %s --write /tmp/fern-log/zfern-wep \
                                                --output-format csv  --encrypt wep %s'"%(wep_display_mode,variables.static_channel,self.monitor_interface))# FOR WEP


    def scan_process4_thread1(self):
        global error_catch
        if bool(variables.xterm_setting):                                             # if True or if xterm contains valid ascii characters
            wpa_display_mode = 'xterm -T "FERN (WPA SCAN)" -geometry 100 -e'
        else:
            wpa_display_mode = ''

        error_catch = variables.exec_command("%s 'airodump-ng -a --channel %s --write /tmp/fern-log/WPA/zfern-wpa \
                                                --output-format csv  --encrypt wpa %s'"%(wpa_display_mode,variables.static_channel,self.monitor_interface))


    def scan_wep(self):
        global xterm_setting
        variables.exec_command('rm -r /tmp/fern-log/*.csv')
        variables.exec_command('rm -r /tmp/fern-log/*.cap')
        variables.exec_command('rm -r /tmp/fern-log/WPA/*.csv')
        variables.exec_command('rm -r /tmp/fern-log/WPA/*.cap')

        # Channel desision block
        if scan_control == 0:
            if not variables.static_channel:
                if len(variables.xterm_setting) == 0:
                    thread.start_new_thread(self.scan_process1_thread,())
                    thread.start_new_thread(self.scan_process1_thread1,())
                else:
                    thread.start_new_thread(self.scan_process2_thread,())
                    thread.start_new_thread(self.scan_process2_thread1,())
            else:
                if len(variables.xterm_setting) == 0:
                    thread.start_new_thread(self.scan_process3_thread,())
                    thread.start_new_thread(self.scan_process3_thread1,())
                else:
                    thread.start_new_thread(self.scan_process4_thread,())
                    thread.start_new_thread(self.scan_process4_thread1,())

        time.sleep(5)
        if scan_control != 1:
            self.label_7.setText(QtGui.QApplication.translate("more", "<font Color=green>\t Active</font>", None, QtGui.QApplication.UnicodeUTF8))

        while scan_control != 1:
            try:
                time.sleep(2)

                wep_access_file = str(reader('/tmp/fern-log/zfern-wep-01.csv'))        # WEP access point log file
                wpa_access_file = str(reader('/tmp/fern-log/WPA/zfern-wpa-01.csv'))     # WPA access point log file

                wep_access_convert = wep_access_file[0:wep_access_file.index('Station MAC')]
                wep_access_process = wep_access_convert[wep_access_convert.index('Key'):-1]
                wep_access_process1 = wep_access_process.strip('Key\r\n')
                process = wep_access_process1.splitlines()

                # Display number of WEP access points detected
                self.wep_count = str(wep_access_file.count('WEP')/2)        # number of access points wep detected

                if int(self.wep_count) > 0:
                    self.emit(QtCore.SIGNAL("wep_number_changed"))
                    self.emit(QtCore.SIGNAL("wep_button_true"))
                else:
                    self.emit(QtCore.SIGNAL("wep_button_false"))

                for iterate in range(len(process)):
                    detail_process1 = process[iterate]
                    wep_access = detail_process1.split(',')

                    mac_address =   wep_access[0].strip(' ')   # Mac address
                    channel =       wep_access[3].strip(' ')   # Channel
                    speed =         wep_access[4].strip(' ')   # Speed
                    power =         wep_access[8].strip(' ')   # Power
                    access_point =  wep_access[13].strip(' ')  # Access point Name

                    if access_point not in wep_details.keys():
                        wep_details[access_point] = [mac_address,channel,speed,power]


                # WPA Access point sort starts here
                read_wpa = reader('/tmp/fern-log/WPA/zfern-wpa-01.csv')

                # Display number of WEP access points detected
                self.wpa_count = str(read_wpa.count('WPA'))        # number of access points wep detected

                if int(self.wpa_count) == 0:
                    self.emit(QtCore.SIGNAL("wpa_button_false"))
                elif int(self.wpa_count >= 1):
                    self.emit(QtCore.SIGNAL("wpa_button_true"))
                    self.emit(QtCore.SIGNAL("wpa_number_changed"))
                else:
                    self.emit(QtCore.SIGNAL("wpa_button_false"))

                wpa_access_convert = wpa_access_file[0:wpa_access_file.index('Station MAC')]
                wpa_access_process = wpa_access_convert[wpa_access_convert.index('Key'):-1]
                wpa_access_process1 = wpa_access_process.strip('Key\r\n')
                process = wpa_access_process1.splitlines()

                for iterate in range(len(process)):
                    detail_process1 = process[iterate]
                    wpa_access = detail_process1.split(',')

                    mac_address =   wpa_access[0].strip(' ')   # Mac address
                    channel =       wpa_access[3].strip(' ')   # Channel
                    speed =         wpa_access[4].strip(' ')   # Speed
                    power =         wpa_access[8].strip(' ')   # Power
                    access_point =  wpa_access[13].strip(' ')  # Access point Name

                    if access_point not in wpa_details.keys():
                        wpa_details[access_point] = [mac_address,channel,speed,power]


            except(ValueError,IndexError):
                pass



    def evaliate_permissions(self):
        if os.geteuid() != 0:
            QtGui.QMessageBox.warning(self,QtGui.QApplication.translate("more", "Insufficient Priviledge", None, QtGui.QApplication.UnicodeUTF8) ,QtGui.QApplication.translate("more", "Aircrack and other dependencies need root priviledge to function, Please run application as root", None, QtGui.QApplication.UnicodeUTF8))
            sys.exit()

