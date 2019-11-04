from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired
import datetime
from itertools import chain


def get_time_windows():
    now = datetime.datetime.now()
    current_year = int(now.year)
    last_y = 2000
    available_range = current_year - last_y
    choices = [((str(i+1)+"y", str(i+1) + " years")) for i in range(available_range)]
    # remove "s" from word "years" in 1 year
    choices[0] = ("1y", "1 year")
    months = [((str(i)+"M", str(i) + " months")) for i in [1,3,6]]
    # remove "s" from word "months" in 1 month
    months[0] = ("1M", "1 month")
    choices = list(chain(months, choices))
    return choices

class AddKeywordForm(FlaskForm):
    new_kw = StringField('New keyword', [DataRequired()], render_kw={"placeholder": "Type new keyword"}, id='new_keyword')

class SubscribeEmailForm(FlaskForm):
    email = StringField('Email', render_kw={"placeholder": "example@example.com"}, id='email')
    kws = StringField('Keywords (comma separated)', render_kw={"placeholder": "keyword1,keyword2"}, id='kws')
    time_limit = SelectField('Time window', choices=[], id="time_limit")
    def __init__(self, *args, **kwargs):
            super(SubscribeEmailForm, self).__init__(*args, **kwargs)
            self.time_limit.choices = get_time_windows()

class TimeWindowForm(FlaskForm):
    #window = SelectField('Time window', choices=get_time_windows())
    window = SelectField('Time window', choices=[])
    def __init__(self, *args, **kwargs):
            super(TimeWindowForm, self).__init__(*args, **kwargs)
            self.window.choices = get_time_windows()
