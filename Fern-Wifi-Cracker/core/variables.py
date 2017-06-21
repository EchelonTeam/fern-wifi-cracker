from core.fern import *

############# WEP/WPA/WPS GLOBAL VARIABLES #################

#
# WPS Variables
#
wps_functions = object()        # Instance of WPS class


#
# Network scan global variable
#
scan_control = 0
static_channel = str()
monitor_interface = str()
monitor_mac_address = str()

xterm_setting = ''
#
# Wep Global variables
#
wep_details = {}
victim_mac = ''
victim_channel = ''
victim_access_point = ''
ivs_number = 0
WEP = ''
digit = 0
ivs_new = ivs_number + digit
#
# Wpa Global variables
#
wpa_details = {}
wpa_victim_mac_address = ''
wpa_victim_channel = ''
wpa_victim_access = ''
control = 0
current_word = ''

################### DIRECTORY GLOBAL VARIABLES ##################
#
# Creating /tmp/ directory for logging of wireless information
#

direc = '/tmp/'
log_direc = 'fern-log'
tmp_direc = os.listdir(direc)                                    # list/tmp/
directory = os.getcwd()

#
# Create temporary log directory
#
if 'fern-log' in tmp_direc:
    commands.getstatusoutput('rm -r %s'%(direc + log_direc))    # Delete directory in /fern-log if it already exists in /tmp/
    os.mkdir(direc + log_direc)
else:
    os.mkdir(direc + log_direc)                                 # Create /tmp/fern-log/

#
# Create Sub Temporary directory in /tmp/fern-log
#
os.mkdir('/tmp/fern-log/WPA')                                     # Create /tmp/fern-log/WPA

#
# Evecute commands without display to stdout
#
def exec_command(command,directory = None):
    output = open(os.devnull,'w')
    ret = subprocess.call(command,shell=True,stdout=output,stderr=output,cwd=directory)
    return(ret)
