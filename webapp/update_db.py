import datetime

from parsing.create_db import parse_laws_into_db
from parsing.notifications import send_email_notifications, clear_bills_changes
from parsing.parsing_options import (email_server, email_acc, email_port, 
                                     email_pass)


year = datetime.datetime.now().year
while year >= 2000:
    prev_year = year - 1
    session = str(prev_year) + '-' + str(year)
    parse_laws_into_db(session=session, num=-1)
    year -= 2

clear_bills_changes()
send_email_notifications(email_server, email_port=email_port, email_pass=email_pass,
                         sender_email=email_acc)