import datetime
import os

from parsing.create_db import parse_laws_into_db
from parsing.notifications import send_email_notifications, clear_bills_changes
from parsing.parsing_options import (email_server, email_acc, email_port, 
                                     email_pass)


abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

year = datetime.datetime.now().year
print(year)
if year % 2 == 0:
    prev_year = year-1
else:
    year+=1
    prev_year = year-1
    
while year >= 2000:
    session = str(prev_year) + '-' + str(year)
    parse_laws_into_db(session=session, num=-1)
    print(session)
    year -= 2
    prev_year -= 2

clear_bills_changes()
send_email_notifications(email_server, email_port=email_port, email_pass=email_pass,
                         sender_email=email_acc)