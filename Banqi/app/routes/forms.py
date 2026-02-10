from flask_wtf import FlaskForm
from wtforms.fields import TextAreaField, SubmitField, StringField, PasswordField, FileField
from wtforms.validators import InputRequired, Length, Email, EqualTo, DataRequired, Regexp, NumberRange
from wtforms.fields.datetime import TimeField, DateField
from wtforms import SelectField, ValidationError, DecimalField, IntegerField
from datetime import time
from datetime import date

import re


# creates the login information
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired("Please enter a username"), Length(max=24, message="Cannot exceed 24 characters long")])
    password=PasswordField("Password", validators=[InputRequired('Please enter your password')])
    submit = SubmitField("Login")

 # this is the registration form
class RegisterForm(FlaskForm):
    @staticmethod
    def chartype_check(form, field):
        username = field.data
        if not re.match("^[A-Za-z0-9_]+$", username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
        if str(username).upper().startswith("ANON"):
            raise ValidationError("Username must not start with ANON as it is reserved for ANONYMUS users only.")
    username = StringField("Username", validators=[InputRequired("Please enter a username"),chartype_check, Length(min=4, max=24, message="Username must be between 4 and 24 characters long")])
    # linking two fields - password should be equal to data entered in confirm
    password=PasswordField("Password", validators=[InputRequired(),
                  EqualTo('confirm', message="Passwords should match"), Length(min=6, message="Password must be at least 6 characters long")])
    confirm = PasswordField("Confirm Password")
    # submit button
    submit = SubmitField("Register")