#
# Regular cron jobs for the fern-wifi-cracker package
#
0 4	* * *	root	[ -x /usr/bin/fern-wifi-cracker_maintenance ] && /usr/bin/fern-wifi-cracker_maintenance
