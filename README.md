# Hospital Management System (HMS)

A web-based Hospital Management System built with Flask, SQLite, and Bootstrap. This application allows Admins to manage hospital records, Doctors to manage appointments and treatments, and Patients to book appointments and view their medical history.

## 📋 Features

## 🏥 Admin (Hospital Staff)

Pre-existing Login: Admin account is created programmatically.

Manage Doctors: Add, update, view, and delete doctor profiles.

Manage Users: Search for doctors and patients by name/ID; delete users if necessary.

View Appointments: Access a master list of all appointments (upcoming and past).

Dashboard: View total counts of doctors, patients, and appointments.

## 👨‍⚕️ Doctor

Dashboard: View upcoming appointments for the day and list of assigned patients.

Appointment Management: Mark appointments as Completed or Cancelled.

Treatments: Add diagnoses, prescriptions, and notes to patient records.

Availability: Update weekly availability notes (e.g., "Mon-Fri 9 AM - 5 PM").

Patient History: View the complete medical history of treated patients.

## 🧑‍tm Patient

Registration: Self-registration and profile management.

Booking: Search doctors by specialization and book appointments (preventing double-booking).

Dashboard: View upcoming appointments and status (Booked/Completed/Cancelled).

Medical History: View past treatments, diagnoses, and prescriptions.

Cancellation: Cancel upcoming appointments.

🛠️ Tech Stack

Backend: Python, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF

Database: SQLite (created programmatically)

Frontend: HTML5, Jinja2, Bootstrap 5

Forms: WTForms with validation

⚙️ Setup & Installation

1. Prerequisites

Python 3.x installed on your machine.

2. Installation Steps

Unzip the project folder or clone the repository.

Open a terminal inside the project folder (HMS_Project/).

Create a virtual environment:
```
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

pip install -r requirements.txt


3. Running the Application

Reset Database (First time only):
Ensure there is no db.sqlite file in the folder (delete it if it exists) to allow the app to generate a fresh database with the default Admin.

Start the server:
```
python3 app.py
```

Open your browser and go to:
```
http://127.0.0.1:5000/
```

## 🔑 Default Credentials

Admin Login

Email: 
```
admin@gmail.com
```

Password: 
```
AdminPass123
```

Doctor Login

Doctors must be created by the Admin first.
Default Password:  (Doctors can change this in "Edit Profile").
```
doctorpass
```


