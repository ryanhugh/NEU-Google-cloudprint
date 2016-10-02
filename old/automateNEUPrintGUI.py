import subprocess
import time

try:
    from pywinauto import application
except ImportError:
    import os.path
    pywinauto_path = os.path.abspath(__file__)
    pywinauto_path = os.path.split(os.path.split(pywinauto_path)[0])[0]
    import sys
    sys.path.append(pywinauto_path)
    from pywinauto import application

import pywinauto
from pywinauto import application
from pywinauto import tests
from pywinauto.timings import Timings

# return true if the pharos printer GUI exists
def winExists():
	return pywinauto.findwindows.find_windows(title="Print job question",visible_only=True)!=[]


def run(title,author,printerName,options):
	if 'husky.neu.edu' not in author:
		print 'Error:',author,'wants to print',title
		return

	print 'Printing',title,'from',author,'duplex=',options['Duplex']
	
	cmdLine=[r'C:\Program Files\Ghostgum\gsview\gsprint.exe','-printer',printerName,'pdf.pdf']
	
	if options['Duplex']!='None':
		cmdLine+=['-duplex_vertical']
    
	subprocess.call(cmdLine)
  	
	while not winExists():
		print 'sleeping...',winExists()
		time.sleep(.5)

	print 'window found'

	#only try three times to plug in the data
	count=0
	while winExists():
		if count>3:
			print 'ERROR: Failed to find GUI, exiting', winExists()
			return

		count+=1

		#attach to pharos GUI
		a=application.Application()
		a.connect_(title = "Print job question")


		#types data
		a.windows_()[0].ClickInput(coords=(200,110))
		a.windows_()[0].TypeKeys(keys=author.partition('@')[0])
		a.windows_()[0].TypeKeys(keys="{TAB 1}")
		a.windows_()[0].TypeKeys(keys=title)
		a.windows_()[0].TypeKeys(keys="{ENTER}")

		print 'Sent keys'

		time.sleep(1)