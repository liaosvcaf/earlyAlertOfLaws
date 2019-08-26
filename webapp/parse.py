from parsing.create_db import parse_laws_into_db
from parsing.notifications import send_email_notifications, clear_bills_changes
from parsing.parsing_options import (email_server, email_acc, email_port, 
                                     email_pass)

clear_bills_changes()
parse_laws_into_db(session="2019-2020", num=-1)
send_email_notifications(email_server, email_port=email_port, email_pass=email_pass,
                         sender_email=email_acc)