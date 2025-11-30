from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db=SQLAlchemy()

class User(db.Model, UserMixin):
    id=db.Column(db.Integer, primary_key=True)
    email=db.Column(db.String(120), unique=True, nullable=False)
    password=db.Column(db.String(255), nullable=False)
    name=db.Column(db.String(120), nullable=False)
    role=db.Column(db.String(20), nullable=False) 
    contact=db.Column(db.String(30))
    specialization = db.Column(db.String(120))
    availability_notes = db.Column(db.Text)  
    age= db.Column(db.Integer)
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
class Appointment(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    patient_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date=db.Column(db.Date, nullable=False)
    time=db.Column(db.String(10), nullable=False)
    status=db.Column(db.String(20), nullable=False, default='Booked') 
    patient=db.relationship('User', foreign_keys=[patient_id], backref='appointments_as_patient')
    doctor=db.relationship('User', foreign_keys=[doctor_id], backref='appointments_as_doctor')

class Treatment(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    appointment_id= db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    diagnosis= db.Column(db.Text)
    prescription=db.Column(db.Text)
    notes=db.Column(db.Text)
    appointment=db.relationship('Appointment', backref='treatment', uselist=True)
