Half of this project works great, but actually sending a print job to neu's servers required an very odd windows server setup to automate the driver GUI and didn't work very well... If theres a better way to submit jobs it could totally be added!

==========
NEU-Google-cloudprint
==========

This project would not be possible without the open source [cloudprint project](https://github.com/armooo/cloudprint).

-----

### Overview

1. Uses [cloudprint](https://github.com/armooo/cloudprint) to download and process the print jobs.
2. Uses [gsprint](http://pages.cs.wisc.edu/~ghost/gsview/gsprint.htm) to print a job on windows from the command line.
3. Automates the Pharos GUI with [pywinauto](https://code.google.com/p/pywinauto/). 

-----

### Setup this project on a new server

There doesn't need to be multiple servers moving print jobs from Google Cloudprint to the Pharos queue, but if you want to setup your own server, here is how to do it. This project is still in the beginning stages, and if find a better way to do something, drop a line!

**The first couple steps are on a linux server:**

2. Install dependancies:
 - `sudo apt-get install cups cups-pdf python-pip` 
 - `sudo pip install cloudprint` 
3. Create four printers in cups to cups-pdf and name them the names of the NEU printers.
4. Download the modified cloudprint.py from linux/cloudprint.py (only one line was added that prints the printer data). 
5. Run cloudprint, and save the printer information it prints out. Save the info as `mainPrinters.txt`.
6. Also save `~/.cloudprintauth` and `~/.cloudprintauth.sasl` 

**The rest of the steps are on a Windows server:**

1. Install the Pharos Printer driver.
2. Install Python 2.7.* 32 bit to `C:\Python2732bit;`
3. Install gsview 5.0 to `C:\Program Files\Ghostgum\gsview` 
4. Download this repository and move `mainPrinters.txt` into the same directory as `run.bat`.
5. Copy `.cloudprintauth` and `.cloudprintauth.sasl` to the home directory of the user on windows. 
6. Run `run.bat`

Note: When the RDP session to the windows server is minimized or closed, the windows server minimizes the windows and pywinauto will no longer work. A quick-fix is to RDP into the server from the server and leave that connection open. 

-----

### Linux

It would be great if this could be ported to linux and avoid the GUI automation, but there is no API for submitting a Pharos print job with a user ID and a title and there is no linux version of the Pharos print driver. Also, it does not seem like the Pharos print driver can be installed in wine.

Related open source projects:

MIT Debathena: Includes the ability to print to MIT Pharos printers through linux cups

Source: [http://debathena.mit.edu/apt/pool/debathena/d/debathena-pharos-support/](http://debathena.mit.edu/apt/pool/debathena/d/debathena-pharos-support/)

GitHub: [https://github.com/mit-athena](https://github.com/mit-athena)

Homepage: [https://debathena.mit.edu/](https://debathena.mit.edu/)

Pharos-linux: [https://github.com/junaidali/pharos-linux](https://github.com/junaidali/pharos-linux)


-----

### Improvements

This project is still in development, and if you find a better way to do something, send a message or open a pull request!
