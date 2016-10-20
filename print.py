#!/usr/bin/env python
# Copyright 2014 Jason Michalski <armooo@armooo.net>
#
# This file is part of cloudprint.
#
# cloudprint is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cloudprint is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cloudprint.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import

import argparse
import datetime
import hashlib
import io
import json
import logging
import logging.handlers
import os
import re
import requests
import shutil
import stat
import sys
import tempfile
import time
import uuid

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders
import os

from cloudprint import xmpp

static_printers = {  
   "PDF":{  
      "printer-is-shared":False,
      "printer-info":"PDF",
      "printer-state-message":"",
      "printer-type":10678348,
      "printer-make-and-model":"Generic CUPS-PDF Printer",
      "printer-state-reasons":[  
         "none"
      ],
      "printer-uri-supported":"ipp://localhost:631/printers/PDF",
      "printer-state":3,
      "printer-location":"",
      "device-uri":"cups-pdf:/"
   }
}

PRINTABLE = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!()+,-.;<=>[\\]^_{|}~ '

static_description = 'PDF'
static_ppd = open('ppd.txt').read()

def getPrinters():
    return static_printers


XMPP_SERVER_HOST = 'talk.google.com'
XMPP_SERVER_PORT = 5223

SOURCE = 'Armooo-PrintProxy-1'
PRINT_CLOUD_SERVICE_ID = 'cloudprint'
CLIENT_LOGIN_URL = '/accounts/ClientLogin'
PRINT_CLOUD_URL = 'https://www.google.com/cloudprint/'

# period in seconds with which we should poll for new jobs via the HTTP api,
# when xmpp is connecting properly.
# 'None' to poll only on startup and when we get XMPP notifications.
# 'Fast Poll' is used as a workaround when notifications are not working.
POLL_PERIOD = 3600.0
FAST_POLL_PERIOD = 30.0

# wait period to retry when xmpp fails
FAIL_RETRY = 60

# how often, in seconds, to send a keepalive character over xmpp
KEEPALIVE = 600.0

# failed job retries
RETRIES = 1
num_retries = 0

LOGGER = logging.getLogger('cloudprint')
LOGGER.setLevel(logging.INFO)

oath = json.loads(open('/etc/cloudprint/oath.json','rb').read())

CLIENT_ID = oath['CLIENT_ID']
CLIENT_KEY = oath['CLIENT_KEY']


def unicode_escape(string):
    return string.encode('unicode-escape').decode('ascii')


class CloudPrintAuth(object):
    AUTH_POLL_PERIOD = 10.0

    def __init__(self, auth_path):
        self.auth_path = auth_path
        self.guid = None
        self.email = None
        self.xmpp_jid = None
        self.exp_time = None
        self.refresh_token = None
        self._access_token = None

    @property
    def session(self):
        s = requests.session()
        s.headers['X-CloudPrint-Proxy'] = 'ArmoooIsAnOEM'
        s.headers['Authorization'] = 'Bearer {0}'.format(self.access_token)
        return s

    @property
    def access_token(self):
        if datetime.datetime.now() > self.exp_time:
            self.refresh()
        return self._access_token

    def no_auth(self):
        return not os.path.exists(self.auth_path)

    def login(self, name, description, ppd):
        self.guid = str(uuid.uuid4())
        reg_data = requests.post(
            PRINT_CLOUD_URL + 'register',
            {
                'output': 'json',
                'printer': name,
                'proxy':  self.guid,
                'capabilities': ppd.encode('utf-8'),
                'defaults': ppd.encode('utf-8'),
                'status': 'OK',
                'description': description,
                'capsHash': hashlib.sha1(ppd.encode('utf-8')).hexdigest(),
            },
            headers={'X-CloudPrint-Proxy': 'ArmoooIsAnOEM'},
        ).json()
        print('Go to {0} to claim this printer'.format(
            reg_data['complete_invite_url']
        ))

        end = time.time() + int(reg_data['token_duration'])
        while time.time() < end:
            time.sleep(self.AUTH_POLL_PERIOD)
            print('trying for the win')
            poll = requests.get(
                reg_data['polling_url'] + CLIENT_ID,
                headers={'X-CloudPrint-Proxy': 'ArmoooIsAnOEM'},
            ).json()
            if poll['success']:
                break
        else:
            print('The login request timedout')

        self.xmpp_jid = poll['xmpp_jid']
        self.email = poll['user_email']
        print('Printer claimed by {0}.'.format(self.email))

        token = requests.post(
            'https://accounts.google.com/o/oauth2/token',
            data={
                'redirect_uri': 'oob',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_KEY,
                'grant_type': 'authorization_code',
                'code': poll['authorization_code'],
            }
        ).json()

        self.refresh_token = token['refresh_token']
        self.refresh()

        self.save()

    def refresh(self):
        token = requests.post(
            'https://accounts.google.com/o/oauth2/token',
            data={
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_KEY,
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
            }
        )
        

        token = token.json()

        self._access_token = token['access_token']

        slop_time = datetime.timedelta(minutes=15)
        expires_in = datetime.timedelta(seconds=token['expires_in'])
        self.exp_time = datetime.datetime.now() + (expires_in - slop_time)

    def load(self):
        if os.path.exists(self.auth_path):
            with open(self.auth_path) as auth_file:
                auth_data = json.load(auth_file)
            self.guid = auth_data['guid']
            self.xmpp_jid = auth_data['xmpp_jid']
            self.email = auth_data['email']
            self.refresh_token = auth_data['refresh_token']

        self.refresh()

    def delete(self):
        if os.path.exists(self.auth_path):
            os.unlink(self.auth_path)

    def save(self):
            if not os.path.exists(self.auth_path):
                with open(self.auth_path, 'w') as auth_file:
                    os.chmod(self.auth_path, stat.S_IRUSR | stat.S_IWUSR)
            with open(self.auth_path, 'w') as auth_file:
                json.dump({
                    'guid':  self.guid,
                    'email': self.email,
                    'xmpp_jid': self.xmpp_jid,
                    'refresh_token': self.refresh_token,
                    },
                    auth_file
                )


class CloudPrintProxy(object):

    def __init__(self, auth):
        self.auth = auth
        self.sleeptime = 0
        self.site = ''
        self.include = []
        self.exclude = []

    def get_printers(self):
        printers = self.auth.session.post(
            PRINT_CLOUD_URL + 'list',
            {
                'output': 'json',
                'proxy': self.auth.guid,
            },
        ).json()
        return [
            PrinterProxy(
                self,
                p['id'],
                re.sub('^' + self.site + '-', '', p['name'])
            )
            for p in printers['printers']
        ]

    def delete_printer(self, printer_id):
        self.auth.session.post(
            PRINT_CLOUD_URL + 'delete',
            {
                'output': 'json',
                'printerid': printer_id,
            },
        ).raise_for_status()
        LOGGER.debug('Deleted printer ' + printer_id)

    def add_printer(self, name, description, ppd):
        if self.site:
            name = self.site + '-' + name
        self.auth.session.post(
            PRINT_CLOUD_URL + 'register',
            {
                'output': 'json',
                'printer': name,
                'proxy':  self.auth.guid,
                'capabilities': ppd.encode('utf-8'),
                'defaults': ppd.encode('utf-8'),
                'status': 'OK',
                'description': description,
                'capsHash': hashlib.sha1(ppd.encode('utf-8')).hexdigest(),
            },
        ).raise_for_status()
        LOGGER.debug('Added Printer ' + name)

    def update_printer(self, printer_id, name, description, ppd):
        if self.site:
            name = self.site + '-' + name
        self.auth.session.post(
            PRINT_CLOUD_URL + 'update',
            {
                'output': 'json',
                'printerid': printer_id,
                'printer': name,
                'proxy': self.auth.guid,
                'capabilities': ppd.encode('utf-8'),
                'defaults': ppd.encode('utf-8'),
                'status': 'OK',
                'description': description,
                'capsHash': hashlib.sha1(ppd.encode('utf-8')).hexdigest(),
            },
        ).raise_for_status()
        LOGGER.debug('Updated Printer ' + name)

    def get_jobs(self, printer_id):
        docs = self.auth.session.post(
            PRINT_CLOUD_URL + 'fetch',
            {
                'output': 'json',
                'printerid': printer_id,
            },
        ).json()

        if 'jobs' not in docs:
            return []
        else:
            return docs['jobs']

    def finish_job(self, job_id):
        self.auth.session.post(
            PRINT_CLOUD_URL + 'control',
            {
                'output': 'json',
                'jobid': job_id,
                'status': 'DONE',
            },
        ).json()
        LOGGER.debug('Finished Job' + job_id)

    def fail_job(self, job_id):
        self.auth.session.post(
            PRINT_CLOUD_URL + 'control',
            {
                'output': 'json',
                'jobid': job_id,
                'status': 'ERROR',
            },
        ).json()
        LOGGER.debug('Failed Job' + job_id)


class PrinterProxy(object):
    def __init__(self, cpp, printer_id, name):
        self.cpp = cpp
        self.id = printer_id
        self.name = name

    def get_jobs(self):
        LOGGER.info('Polling for jobs on ' + self.name)
        return self.cpp.get_jobs(self.id)

    def update(self, description, ppd):
        return self.cpp.update_printer(self.id, self.name, description, ppd)

    def delete(self):
        return self.cpp.delete_printer(self.id)

def get_printer_info():
    return static_ppd, static_description

def sendMail(to, fro, subject, text, name, fileData=[],server="localhost"):
    assert type(to)==list
    assert type(fileData)==list


    msg = MIMEMultipart()
    msg['From'] = fro
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach( MIMEText(text) )

    for file in fileData:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(file)
        Encoders.encode_base64(part)
        if not name.endswith('.pdf'):
        	name = name + '.pdf'
        
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % name)
        msg.attach(part)

    smtp = smtplib.SMTP(server)
    smtp.sendmail(fro, to, msg.as_string() )
    smtp.close()


def process_job(cpp, printer, job):
    global num_retries

    try:
        pdf = cpp.auth.session.get(job['fileUrl'], stream=True)

        options = cpp.auth.session.get(job['ticketUrl']).json()
        if 'request' in options:
            del options['request']

        options = dict((str(k), str(v)) for k, v in list(options.items()))
        

        rawData = pdf.raw.read()
        
        if len(job['title']) == 0:
        	job['title'] = 'document'
        
        # Remove all non-whitelisted characters.
        job['title'] = filter(lambda x: x in PRINTABLE, job['title'])
        
		# Trim job title down to 30 characters
        if len(job['title']) > 30:
            job['title'] = job['title'][:30]
            print 'Trimmed length of title', job['title']

        if len(job['title']) == 0:
        	job['title'] = 'document'
		

        if not job['ownerId'].endswith('husky.neu.edu'):
            print 'Sending invalid username email to ', job['ownerId']
            sendMail(['user <' + job['ownerId'] +'>'],'printbot <theprintbot@thisdomaindoesnotexisthithere.com>','Need a husky.neu.edu email to print!','Hey! \n\nI need a @husky.neu.edu email to print to Northeastern\'s printers. Please use your @husky.neu.edu to print!', '')
        else:
            print job['ownerId'], job['title'],'Size is',len(rawData)
            # sendMail(['mobileprinting <rysquash@gmail.com>'],'hi <' + job['ownerId'] + '>','hi','hi', job['title'], [rawData])
            sendMail(['mobileprinting <mobileprinting@neu.edu>'],'hi <' + job['ownerId'] + '>','hi','hi', job['title'], [rawData])

        LOGGER.info(unicode_escape('SUCCESS ' + job['title']))

        cpp.finish_job(job['id'])
        num_retries = 0

    except Exception as e:
        print e
        if num_retries >= RETRIES:
            num_retries = 0
            cpp.fail_job(job['id'])
            LOGGER.error(unicode_escape('ERROR ' + job['title']))
            raise
        else:
            num_retries += 1
            LOGGER.info(
                unicode_escape('Job %s failed - Will retry' % job['title'])
            )


def process_jobs(cpp):
    xmpp_conn = xmpp.XmppConnection(keepalive_period=KEEPALIVE)

    while True:
        process_jobs_once(cpp, xmpp_conn)


def process_jobs_once(cpp, xmpp_conn):
    printers = cpp.get_printers()
    try:
        for printer in printers:
            for job in printer.get_jobs():
                process_job(cpp, printer, job)

        if not xmpp_conn.is_connected():
            xmpp_conn.connect(XMPP_SERVER_HOST, XMPP_SERVER_PORT, cpp.auth)

        xmpp_conn.await_notification(cpp.sleeptime)

    except Exception:
        LOGGER.exception(
            'ERROR: Could not Connect to Cloud Service. '
            'Will Try again in %d Seconds' %
            FAIL_RETRY
        )
        time.sleep(FAIL_RETRY)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d',
        dest='daemon',
        action='store_true',
        help='enable daemon mode (requires the daemon module)',
    )
    parser.add_argument(
        '-l',
        dest='logout',
        action='store_true',
        help='logout of the google account',
    )
    parser.add_argument(
        '-p',
        metavar='pid_file',
        dest='pidfile',
        default='cloudprint.pid',
        help='path to write the pid to (default %(default)s)',
    )
    parser.add_argument(
        '-a',
        metavar='account_file',
        dest='authfile',
        default=os.path.expanduser('~/.cloudprintauth.json'),
        help='path to google account ident data (default %(default)s)',
    )
    parser.add_argument(
        '-c',
        dest='authonly',
        action='store_true',
        help='establish and store login credentials, then exit',
    )
    parser.add_argument(
        '-f',
        dest='fastpoll',
        action='store_true',
        help='use fast poll if notifications are not working',
    )
    parser.add_argument(
        '-v',
        dest='verbose',
        action='store_true',
        help='verbose logging',
    )
    parser.add_argument(
        '--syslog-address',
        help='syslog address to use in daemon mode',
    )
    parser.add_argument(
        '-s',
        metavar='sitename',
        dest='site',
        default='',
        help='one-word site-name theat will prefix printers',
    )

    parser.add_argument(
        '--debug',
        metavar='debug',
        dest='debug',
        default=False,
        help='Enable debug mode. This will send emails to the email that sent them instead of to mobileprinting@neu.edu.',
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.syslog_address and not args.daemon:
        print('syslog_address is only valid in daemon mode')
        sys.exit(1)

    # if daemon, log to syslog, otherwise log to stdout
    if args.daemon:
        if args.syslog_address:
            handler = logging.handlers.SysLogHandler(
                address=args.syslog_address
            )
        else:
            handler = logging.handlers.SysLogHandler()
        handler.setFormatter(
            logging.Formatter(fmt='cloudprint.py: %(message)s')
        )
    else:
        handler = logging.StreamHandler(sys.stdout)
    LOGGER.addHandler(handler)

    if args.verbose:
        LOGGER.info('Setting DEBUG-level logging')
        LOGGER.setLevel(logging.DEBUG)

        try:
            import http.client as httpclient
        except ImportError:
            import httplib as httpclient
        httpclient.HTTPConnection.debuglevel = 1

        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    auth = CloudPrintAuth(args.authfile)
    if args.logout:
        auth.delete()
        LOGGER.info('logged out')
        return

    cpp = CloudPrintProxy(auth)

    cpp.sleeptime = POLL_PERIOD
    if args.fastpoll:
        cpp.sleeptime = FAST_POLL_PERIOD

    cpp.site = args.site

    printers = list(getPrinters().keys())
    if not printers:
        LOGGER.error('No printers found')
        return

    if auth.no_auth():
        name = printers[0]
        ppd, description = get_printer_info()
        auth.login(name, description, ppd)
    else:
        auth.load() 

    if args.authonly:
        sys.exit(0)

    if args.daemon:
        try:
            import daemon
            import daemon.pidfile
        except ImportError:
            print('daemon module required for -d')
            print(
                '\tyum install python-daemon, or apt-get install '
                'python-daemon, or pip install python-daemon'
            )
            sys.exit(1)

        pidfile = daemon.pidfile.TimeoutPIDLockFile(
            path=os.path.abspath(args.pidfile),
            timeout=5,
        )
        with daemon.DaemonContext(pidfile=pidfile):
            process_jobs(cpp)

    else:
        process_jobs(cpp)


if __name__ == '__main__':
    main()
