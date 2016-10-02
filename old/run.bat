@echo off

 rem script to run cloudprint.py on the windows server

set PATH=%PATH%;C:\Python2732bit;C:\Program Files\Ghostgum\gsview

python -u cloudprint.py >> output.txt 2>> error.txt
pause