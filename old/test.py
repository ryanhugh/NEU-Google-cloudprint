import subprocess
import time


#small testing script for pywinauto

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


a=application.Application()
print pywinauto.findwindows.find_windows(title="Print job question",visible_only=True)!=[]