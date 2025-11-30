from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, Length, Optional
class LoginForm(FlaskForm):
    email=StringField('Email', validators=[DataRequired(), Email()])
    password=PasswordField('Password', validators=[DataRequired()])
    submit=SubmitField('Login')
class RegisterForm(FlaskForm):
    name=StringField('Full Name',validators=[DataRequired()])
    email=StringField('Email', validators=[DataRequired(), Email()])
    password=PasswordField('Password',validators=[DataRequired()])
    contact=StringField('Contact',validators=[DataRequired()])
    age=IntegerField('Age',validators=[DataRequired()])
    submit=SubmitField('Register')

class DoctorForm(FlaskForm):
    name=StringField('Name', validators=[DataRequired()])
    email=StringField('Email', validators=[DataRequired(),Email()])
    specialization=StringField('Specialization', validators=[DataRequired()])
    contact=StringField('Contact')
    submit=SubmitField('Save Doctor')
class AppointmentForm(FlaskForm):
    doctor=SelectField('Doctor', coerce=int, validators=[DataRequired()])
    date=DateField('Date',validators=[DataRequired()])
    time=SelectField('Time',choices=[
        ('09:00', '09:00 AM'), ('10:00','10:00 AM'), ('11:00','11:00 AM'),
        ('12:00','12:00 PM'), ('14:00','02:00 PM'), ('15:00','03:00 PM'),
        ('16:00','04:00 PM'), ('17:00','05:00 PM')
    ], validators=[DataRequired()])
    submit = SubmitField('Book Appointment')

class ProfileForm(FlaskForm):
    name=StringField('Full Name', validators=[DataRequired()])
    contact=StringField('Contact', validators=[DataRequired()])
    specialization = StringField('Specialization (Doctors Only)', validators=[Optional()])
    age=IntegerField('Age (Patients Only)', validators=[Optional()])
    password=PasswordField('New Password (leave blank)', validators=[Optional()])
    submit=SubmitField('Update Profile')

class AvailabilityForm(FlaskForm):
    notes=TextAreaField('Availability (e.g., "Mon-Fri, 9AM - 5PM")', validators=[DataRequired()])
    submit=SubmitField('Update Availability')
