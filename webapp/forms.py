from wtforms import Form, StringField, SelectField, SubmitField, DateField, validators
from wtforms.validators import DataRequired, Required
import datetime

def get_sessions():
    now = datetime.datetime.now()
    current_year = int(now.year)
    next_y = current_year + 1
    last_y = 1999
    choices = []
    year = next_y
    while year > last_y:
        prev_year = year - 1
        session = str(prev_year) + '-' + str(year)
        year -= 1
        choices.append((session, session))
    choices.reverse()
    return choices

class SimpleSearchForm(Form):
    search = StringField('search', [DataRequired()])
    submit = SubmitField('Search', render_kw={'class': 'btn btn-success btn-block'})

class AdvancedSearchForm(Form):
    title = StringField('title', render_kw={"placeholder": "Title"})
    text = StringField('text', render_kw={"placeholder": "Bill text"})
    subject = StringField('subject', render_kw={"placeholder": "Subject"})
    bill_code = StringField('bill_code', render_kw={"placeholder": "Bill code"})
    authors = StringField('authors', render_kw={"placeholder": "Authors"})

    last_amendment_date = DateField('Last amendment date', [Required(message='Input must be of YYYY-MM-DD format.')])  
    
    session_dropdown_list = get_sessions()
    session = SelectField('Session', choices=session_dropdown_list, default=1)
    
    house_location_dropdown_list = [('assembly', 'Assembly'), ('senate', 'Senate')]
    house_location = SelectField('House Location', choices=house_location_dropdown_list, default=1)
    
    submit = SubmitField('Search', render_kw={'class': 'btn btn-success btn-block'})

print(get_sessions())