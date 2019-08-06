from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

class AddKeywordForm(FlaskForm):
    new_kw = StringField('New keyword', [DataRequired()], render_kw={"placeholder": "Type new keyword"}, id='new_keyword')
