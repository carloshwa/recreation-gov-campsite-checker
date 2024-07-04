from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Set
import smtplib
import random
import sys
import os
import time

from hashlib import md5

from enums.emoji import Emoji

# Janky simple argument parsing.
if len(sys.argv) < 2:
    print("Please provide the user you want to tweet at!")
    sys.exit(1)

sayMessage = sys.argv[1]
campsiteId = sys.argv[2]

recipient = os.getenv('RECGOV_EMAIL_RECEIVER')
sender = os.getenv('RECGOV_EMAIL_SENDER')
password = os.getenv('RECGOV_EMAIL_PW')

available_site_strings = []
for line in sys.stdin:
    line = line.strip()
    if Emoji.SUCCESS.value in line:
        os.system("say {}".format(sayMessage))
        name = " ".join(line.split(":")[0].split(" ")[1:])
        available = line.split(":")[1][1].split(" ")[0]
        s = "{} site(s) available in {}".format(available, name)
        available_site_strings.append(s)

if available_site_strings:
    tweet = " 🏕🏕🏕\n" + "\n".join(available_site_strings)
    print(tweet)

    subject = "Campsite available!"

    server = smtplib.SMTP('smtp.gmail.com', 587)
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(tweet + '\nhttps://www.recreation.gov/camping/campgrounds/' + campsiteId))

    server.starttls()
    server.login(sender, password)
    server.sendmail(
        sender,
        recipient,
        msg.as_string()
    )
else:
    print("No campsites available, not tweeting 😞")

