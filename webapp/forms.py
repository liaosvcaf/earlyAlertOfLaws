from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired
import datetime

    
def get_time_winows():
    now = datetime.datetime.now()
    current_year = int(now.year)
    last_y = 2000
    available_range = current_year - last_y
    choices = [((i+1, str(i+1) + " years")) for i in range(available_range)]
    # remove "s" from word "years" in 1 year
    choices[0] = (1, "1 year")
    return choices


class AddKeywordForm(FlaskForm):
    new_kw = StringField('New keyword', [DataRequired()], render_kw={"placeholder": "Type new keyword"}, id='new_keyword')

class SubscribeEmailForm(FlaskForm):
    email = StringField('Email', render_kw={"placeholder": "example@example.com"}, id='email')
    kws = StringField('Keywords (comma separated)', render_kw={"placeholder": "keyword1,keyword2"}, id='kws')
    time_limit = SelectField('Time window', choices=get_time_winows(), id="time_limit", default=1)

class TimeWindowForm(FlaskForm):
    window = SelectField('Time window', choices=get_time_winows(), default=1)
