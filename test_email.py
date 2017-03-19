import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

import random
import time

# Small file to manually test the email part of the project

# gmail-smtp-in.l.google.com is the server for sending to @gmail.com
def sendMail(to, fro, subject, text, name, fileData=[], server="northeastern-edu.mail.protection.outlook.com"):
    assert type(to)==list
    assert type(fileData)==list


    msg = MIMEMultipart()
    msg['From'] = fro
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg['Message-ID'] = 'neuprint_dot_org_email_' + str(random.random()) + '_' + str(time.time())

    msg.attach( MIMEText(text) )

    for file in fileData:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(file)
        Encoders.encode_base64(part)
        if not name.endswith('.pdf'):
        	name = name + '.pdf'
        
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % name)
        msg.attach(part)

    # print msg.as_string()
    # print fileData

    smtp = smtplib.SMTP(server)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.sendmail(fro, to, msg.as_string() )
    smtp.close()



sendMail(['mobileprinting@neu.edu'], 'Ryan Hughes <... @husky.neu.edu>', 'Automatic Print via neuprint dot org', 'This document has been printed by Ryan Hughes via neuprint dot org.', 'document_name_here', [open('blank_pdf.pdf','rb').read()])