from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField, SelectField, DateField, FileField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")

class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField("Confirm Password", validators=[EqualTo("password")])
    submit = SubmitField("Create Account")

class ReportItemForm(FlaskForm):
    name = StringField("Item Name", validators=[DataRequired(), Length(max=140)])
    description = TextAreaField("Description", validators=[DataRequired(), Length(max=2000)])
    category = SelectField("Category", coerce=int, validators=[DataRequired()])
    location_found = StringField("Location Found", validators=[DataRequired(), Length(max=140)])
    date_found = DateField("Date Found", validators=[DataRequired()], default=date.today)
    photo = FileField("Upload Photo (optional)")
    submit = SubmitField("Submit")

class SearchForm(FlaskForm):
    q = StringField("Search", validators=[Optional(), Length(max=140)])
    category = SelectField("Category", coerce=int, validators=[Optional()])
    sort = SelectField("Sort By", choices=[("date_desc","Newest"),("date_asc","Oldest"),("category","Category")])
    submit = SubmitField("Apply")
