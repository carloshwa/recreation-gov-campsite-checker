import random
import sys
import os
import time

from hashlib import md5

from camping import SUCCESS_EMOJI


available_site_strings = []
for line in sys.stdin:
    line = line.strip()
    if SUCCESS_EMOJI in line:
        os.system('say campsite found')
        name = " ".join(line.split(":")[0].split(" ")[1:])
        available = line.split(":")[1][1].split(" ")[0]
        s = "{} site(s) available in {}".format(available, name)
        available_site_strings.append(s)

if available_site_strings:
    tweet = " 🏕🏕🏕\n" + "\n".join(available_site_strings)
    print(tweet)
else:
    print("No campsites available, not tweeting 😞")
