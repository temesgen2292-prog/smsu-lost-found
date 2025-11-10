from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField, SelectField,
    DateField, FileField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, ValidationError
from email_validator import validate_email, EmailNotValidError
from flask import current_app

# ---- Custom validators -------------------------------------------------------

def smsudomain(form, field):
    """Allow only SMSU/MinnState emails on registration."""
    try:
        info = validate_email(field.data, check_deliverability=False)
        domain = info.domain.lower()
    except EmailNotValidError as e:
        raise ValidationError("Enter a valid email address.")
    allowed = current_app.config.get("ALLOWED_EMAIL_DOMAINS", set())
    if domain not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise ValidationError(f"Use your official email ({allowed_list}).")

def strong_password(form, field):
    """Simple local check—length >= 6 and no all-spaces."""
    pwd = (field.data or "").strip()
    if len(pwd) < 6:
        raise ValidationError("Password must be at least 6 characters.")

# ---- Forms ------------------------------------------------------------------

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")

class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), smsudomain])
    password = PasswordField("Password", validators=[DataRequired(), strong_password])
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
    sort = SelectField("Sort By", choices=[
        ("date_desc","Newest"),("date_asc","Oldest"),("category","Category")
    ])
    submit = SubmitField("Apply")
