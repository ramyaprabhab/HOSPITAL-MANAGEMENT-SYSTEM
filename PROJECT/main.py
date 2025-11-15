# --- Standard Python Library ---
import json
from datetime import datetime, time
from functools import wraps

# --- Core Flask ---
from flask import (
    Flask, render_template, request, 
    session, redirect, url_for, flash
)

# --- Flask Extensions ---
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    UserMixin, login_user, logout_user, 
    LoginManager, login_required, current_user
)
from flask_mail import Mail

# --- Other Third-Party Libraries ---
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_


local_server= True
app = Flask(__name__)
app.secret_key='mayank'


# this is for getting unique user access
login_manager=LoginManager(app)
login_manager.login_view='login'

# SMTP MAIL SERVER SETTINGS

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=" gmail-id",
    MAIL_PASSWORD=" gmail-password"
)
mail = Mail(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rammidoc.db'
db=SQLAlchemy(app)


# ... after db=SQLAlchemy(app) ...

class Test(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100))
    email=db.Column(db.String(100))

# User model is mostly the same
class User(UserMixin,db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(50))
    usertype=db.Column(db.String(50)) # 'Patient', 'Doctor', 'Admin'
    email=db.Column(db.String(50),unique=True)
    password=db.Column(db.String(1000))
    
    # Add relationship: A User (Patient) can have many appointments
    appointments = db.relationship('Appointment', back_populates='patient', foreign_keys='Appointment.patient_id')

class Doctors(db.Model):
    did=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(50))
    doctorname=db.Column(db.String(50))
    dept=db.Column(db.String(50))
    
    # Add relationship: A Doctor can have many appointments
    appointments = db.relationship('Appointment', back_populates='doctor', foreign_keys='Appointment.doctor_id')
    # Add relationship: A Doctor can have many availability entries
    availability_schedule = db.relationship('DoctorAvailability', back_populates='doctor', cascade="all, delete-orphan")


# NEW: This is your old 'Patients' model, renamed and fixed
class Appointment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    time=db.Column(db.String(50),nullable=False)
    date=db.Column(db.String(50),nullable=False)
    disease=db.Column(db.String(50)) # Kept from your old model
    
    # --- NEW REQUIRED FIELDS ---
    status=db.Column(db.String(50), default='Booked') # "Booked", "Completed", "Cancelled"
    
    # --- NEW FOREIGN KEYS ---
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.did'), nullable=False)
    
    # --- NEW RELATIONSHIPS ---
    # Links this Appointment to the User who is the patient
    patient = db.relationship('User', back_populates='appointments', foreign_keys=[patient_id])
    # Links this Appointment to the Doctor
    doctor = db.relationship('Doctors', back_populates='appointments', foreign_keys=[doctor_id])
    # Links this Appointment to its treatment record
    treatment = db.relationship('Treatment', back_populates='appointment', uselist=False) # one-to-one

# NEW: Model for Treatment/History
class Treatment(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    diagnosis=db.Column(db.Text, nullable=True)
    prescription=db.Column(db.Text, nullable=True)
    notes=db.Column(db.Text, nullable=True)
    
    # --- NEW FOREIGN KEY ---
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    
    # --- NEW RELATIONSHIP ---
    appointment = db.relationship('Appointment', back_populates='treatment')


class DoctorAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_name = db.Column(db.String(10)) # e.g., "Monday", "Tuesday"
    start_time = db.Column(db.String(5), nullable=True) # e.g., "09:00"
    end_time = db.Column(db.String(5), nullable=True)   # e.g., "17:00"
    
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.did'), nullable=False)
    doctor = db.relationship('Doctors', back_populates='availability_schedule')


# We can keep Trigr, but it should be updated to watch the 'Appointment' table
class Trigr(db.Model):
    tid=db.Column(db.Integer,primary_key=True)
    pid=db.Column(db.Integer)
    email=db.Column(db.String(50))
    name=db.Column(db.String(50))
    action=db.Column(db.String(50))
    timestamp=db.Column(db.String(50))



@app.route('/')
def index():
    return render_template('index.html')
    


@app.route('/doctors',methods=['POST','GET'])
def doctors():

    if request.method=="POST":

        email=request.form.get('email')
        doctorname=request.form.get('doctorname')
        dept=request.form.get('dept')

        new_doctor = Doctors(email=email, doctorname=doctorname, dept=dept)
        db.session.add(new_doctor)
        db.session.commit()
        flash("Information is Stored","primary")

    return render_template('doctor.html')



@app.route('/patients',methods=['POST','GET'])
@login_required
def patient():
    # GET request: Just show the form and the list of doctors
    doct=Doctors.query.all()

    if request.method=="POST":
        # Get data from the form
        time=request.form.get('time')
        date_str=request.form.get('date') # Renamed to avoid confusion
        disease=request.form.get('disease')
        doctor_id=request.form.get('doctor_id') 

        # --- NEW: Doctor Availability Check ---
        try:
            # 1. Convert date string to datetime object
            booking_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # 2. Get the full day name (e.g., "Thursday")
            day_name = booking_date_obj.strftime('%A')
        except ValueError:
            flash("Invalid date format. Please try again.", "danger")
            return render_template('patient.html',doct=doct)

        # 3. Find the doctor's schedule for that day
        doctor_schedule = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            day_name=day_name
        ).first()

        # 4. Get the doctor's info for flash messages
        doctor = Doctors.query.get(doctor_id)

        # 5. Validation Check 1: Is the doctor working at all?
        if not doctor_schedule or not doctor_schedule.start_time or not doctor_schedule.end_time:
            flash(f"Dr. {doctor.doctorname} is not available on {day_name}s. Please select a different day.", "danger")
            return render_template('patient.html',doct=doct)

        # 6. Validation Check 2: Is the time within working hours?
        # We can compare times as strings (e.g., "09:00" <= "10:30" < "17:00")
        if not (doctor_schedule.start_time <= time < doctor_schedule.end_time):
            flash(f"The selected time {time} is outside Dr. {doctor.doctorname}'s hours ({doctor_schedule.start_time} - {doctor_schedule.end_time}) on {day_name}s.", "danger")
            return render_template('patient.html',doct=doct)
        
        # --- END OF NEW LOGIC ---

        # --- CORE REQUIREMENT: Check for conflicts (Existing Logic) ---
        conflict = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=date_str, # Use the string version
            time=time
        ).first()

        if conflict:
            flash(f"Dr. {doctor.doctorname} is already booked at {time} on {date_str}. Please choose another time.", "danger")
            return render_template('patient.html',doct=doct)
        
        # --- Create the new appointment ---
        new_appointment = Appointment(
            time=time,
            date=date_str, # Use the string version
            disease=disease,
            status='Booked',
            patient_id=current_user.id, # Link to the logged-in patient
            doctor_id=doctor_id         # Link to the chosen doctor
        )

        db.session.add(new_appointment)
        db.session.commit()
        
        # You can re-enable your mail send logic here if you want
        # mail.send_message(...)

        flash("Booking Confirmed!","info")
        return redirect(url_for('bookings')) # Redirect to see the booking


    return render_template('patient.html',doct=doct)

@app.route('/bookings')
@login_required
def bookings(): 
    if current_user.usertype=="Doctor":
        # Find the doctor profile linked to the logged-in user's email
        doctor = Doctors.query.filter_by(email=current_user.email).first()
        
        if doctor:
            # Doctor sees appointments linked to their doctor_id
            query = Appointment.query.filter_by(doctor_id=doctor.did).order_by(Appointment.date, Appointment.time).all()
        else:
            query = [] # Or flash a message "Please complete your doctor profile"
        
        return render_template('booking.html',query=query)
    
    else: # Assumes "Patient"
        # Patient sees appointments linked to their patient_id
        query = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.date, Appointment.time).all()
        return render_template('booking.html',query=query)
    


@app.route("/edit/<int:id>",methods=['POST','GET']) # Use <int:id>
@login_required
def edit(id):
    # Find the appointment by its ID
    appointment = Appointment.query.get_or_404(id)

    # --- Security Check: Only the patient can edit their own appointment ---
    if appointment.patient_id != current_user.id:
        flash("You do not have permission to edit this appointment.", "danger")
        return redirect(url_for('bookings'))

    if request.method=="POST":
        # Get new details from form
        new_time=request.form.get('time')
        new_date=request.form.get('date')
        
        # --- Conflict Check ---
        conflict = Appointment.query.filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.date == new_date,
            Appointment.time == new_time,
            Appointment.id != id  # Exclude the appointment itself
        ).first()

        if conflict:
            flash(f"That time slot is already booked. Please choose another.", "danger")
            return render_template('edit.html', posts=appointment) # Stay on page

        # Update the appointment
        appointment.time = new_time
        appointment.date = new_date
        appointment.disease = request.form.get('disease')
        # You could also update gender, slot, dept, number if they are part of the
        # appointment, but they should really be part of the User (Patient) profile.
        # For now, we just update what's in the model.
        
        db.session.commit()
        flash("Appointment Successfully Updated","success")
        return redirect('/bookings')
    
    # GET request: show the edit form
    return render_template('edit.html',posts=appointment)


@app.route("/delete/<int:id>",methods=['POST','GET']) # Use <int:id>
@login_required
def delete(id):
    appointment = Appointment.query.get_or_404(id)

    # --- Security Check: Only the patient can cancel ---
    if appointment.patient_id != current_user.id:
        flash("You do not have permission to cancel this appointment.", "danger")
        return redirect(url_for('bookings'))

    # --- Update status instead of deleting ---
    appointment.status = "Cancelled"
    db.session.commit()
    
    flash("Appointment Successfully Cancelled","warning")
    return redirect('/bookings')


@app.route('/signup',methods=['POST','GET'])
def signup():
    if request.method == "POST":
        username=request.form.get('username')
        usertype=request.form.get('usertype')
        email=request.form.get('email')
        password=request.form.get('password')
        user=User.query.filter_by(email=email).first()
        if user:
            flash("Email Already Exist","warning")
            return render_template('/signup.html')
        encpassword=generate_password_hash(password)

        new_user = User(
        username=username, 
        usertype=usertype, 
        email=email, 
        password=encpassword
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Signup Succes Please Login","success")
        return render_template('login.html')

          

    return render_template('signup.html')

@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == "POST":
        email=request.form.get('email')
        password=request.form.get('password')
        user=User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password,password):
            login_user(user)
            flash("Login Success","primary")
            return redirect(url_for('index'))
        else:
            flash("invalid credentials","danger")
            return render_template('login.html')    





    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout SuccessFul","warning")
    return redirect(url_for('login'))

@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
def doctor_availability():
    # Security Check: Must be a Doctor
    if current_user.usertype != 'Doctor':
        flash("You are not authorized to view this page.", "danger")
        return redirect(url_for('index'))

    # Find the doctor's profile
    doctor = Doctors.query.filter_by(email=current_user.email).first()
    if not doctor:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # --- Handle the form submission ---
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        try:
            for day in days_of_week:
                is_unavailable = request.form.get(f'unavailable_{day}')
                start_time = request.form.get(f'start_time_{day}')
                end_time = request.form.get(f'end_time_{day}')

                # Find this day's record in the database
                availability_record = DoctorAvailability.query.filter_by(
                    doctor_id=doctor.did,
                    day_name=day
                ).first()

                if is_unavailable:
                    # If "Unavailable" is checked, set times to None
                    availability_record.start_time = None
                    availability_record.end_time = None
                elif start_time and end_time:
                    # If both times are provided, save them
                    availability_record.start_time = start_time
                    availability_record.end_time = end_time
                else:
                    # If only one time is provided or both are blank, set to None
                    availability_record.start_time = None
                    availability_record.end_time = None

            db.session.commit()
            flash("Availability updated successfully!", "success")
        
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "danger")

        return redirect(url_for('doctor_availability'))

    # --- GET Request: Show the page ---
    # Fetch the 7-day schedule for this doctor
    schedule = DoctorAvailability.query.filter_by(doctor_id=doctor.did).all()
    
    # Sort them in the correct weekday order
    day_order = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7}
    schedule.sort(key=lambda x: day_order[x.day_name])

    return render_template('doctor_manage_availability.html', schedule=schedule)

@app.route('/test')
def test():
    try:
        Test.query.all()
        return 'My database is Connected'
    except:
        return 'My db is not Connected'
    

@app.route('/details')
@login_required
def details():
    posts=db.engine.execute("SELECT * FROM `trigr`")
    return render_template('trigers.html',posts=posts)


@app.route('/search',methods=['POST','GET'])
@login_required
def search():
    if request.method=="POST":
        query=request.form.get('search')
        dept=Doctors.query.filter_by(dept=query).first()
        name=Doctors.query.filter_by(doctorname=query).first()
        if name:

            flash("Doctor is Available","info")
        else:

            flash("Doctor is Not Available","danger")
    return render_template('index.html')

@app.route('/treatment/add/<int:id>', methods=['GET', 'POST'])
@login_required
def add_treatment(id):
    # Security check: Must be a doctor
    if current_user.usertype != 'Doctor':
        flash("You are not authorized to perform this action.", "danger")
        return redirect(url_for('bookings'))

    appointment = Appointment.query.get_or_404(id)

    # Security check: Doctor can only edit their own appointments
    doctor = Doctors.query.filter_by(email=current_user.email).first()
    if appointment.doctor_id != doctor.did:
        flash("This appointment is not assigned to you.", "danger")
        return redirect(url_for('bookings'))

    if request.method == 'POST':
        # Get data from form
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')

        # Create the new treatment record
        new_treatment = Treatment(
            diagnosis=diagnosis,
            prescription=prescription,
            notes=notes,
            appointment_id=appointment.id
        )

        # Update the appointment status
        appointment.status = 'Completed'

        db.session.add(new_treatment)
        db.session.commit() # This saves both the new treatment and the status change

        flash("Treatment saved and appointment marked as 'Completed'.", "success")
        return redirect(url_for('bookings'))

    # GET Request: Show the form
    return render_template('treatment.html', appointment=appointment, readonly="")

@app.route('/treatment/view/<int:id>')
@login_required
def view_treatment(id):
    appointment = Appointment.query.get_or_404(id)
    treatment = Treatment.query.filter_by(appointment_id=id).first()

    # Security check: Allow Patient or assigned Doctor
    if current_user.usertype == 'Patient' and appointment.patient_id == current_user.id:
        pass # Allow patient to view
    elif current_user.usertype == 'Doctor':
        doctor = Doctors.query.filter_by(email=current_user.email).first()
        if appointment.doctor_id != doctor.did:
            flash("You are not authorized to view this.", "danger")
            return redirect(url_for('bookings'))
    else:
        flash("You are not authorized to view this.", "danger")
        return redirect(url_for('bookings'))

    if not treatment:
        flash("Treatment has not been added yet.", "info")
        return redirect(url_for('bookings'))
        
    # Render the same template, but with fields disabled
    return render_template('treatment.html', appointment=appointment, treatment=treatment, readonly="readonly")


def admin_required(f):
    """
    Decorator to ensure a user is an Admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.usertype != 'Admin':
            flash("You must be an Admin to view this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin/patients', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_manage_patients():
    if request.method == 'POST':
        # Handle search
        query = request.form.get('search_query', '')
        search_term = f"%{query}%"
        # Search by username or email, case-insensitive
        patients = User.query.filter(
            User.usertype == 'Patient',
            or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term)
            )
        ).all()
        page_title = f"Search Results for '{query}'"
    else:
        # GET request: Show all patients
        patients = User.query.filter_by(usertype='Patient').all()
        page_title = "Manage All Patients"
        
    return render_template('admin_manage_patients.html', patients=patients, title=page_title)


@app.route('/admin/patients/delete/<int:id>')
@login_required
@admin_required
def admin_delete_patient(id):
    patient_to_delete = User.query.get_or_404(id)

    # Security check: Make sure this is a patient
    if patient_to_delete.usertype != 'Patient':
        flash("This user is not a patient.", "danger")
        return redirect(url_for('admin_manage_patients'))

    # --- Dependency Check (CRITICAL) ---
    # Before deleting a patient, we must check if they have appointments.
    appointments = Appointment.query.filter_by(patient_id=id).first()
    if appointments:
        flash("Cannot delete patient. They have existing appointments in the system. Please cancel appointments first.", "danger")
        return redirect(url_for('admin_manage_patients'))
        
    # If no appointments, proceed with deletion
    db.session.delete(patient_to_delete)
    db.session.commit()
    
    flash("Patient deleted successfully.", "success")
    return redirect(url_for('admin_manage_patients'))


@app.route('/admin/doctors', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_manage_doctors():
    # This route handles POST (Adding a new doctor)
    if request.method == 'POST':
        name = request.form.get('doctorname')
        email = request.form.get('email')
        dept = request.form.get('dept')
        password = request.form.get('password')

        # Check if user (doctor) or doctor profile already exists
        user_exists = User.query.filter_by(email=email).first()
        doctor_exists = Doctors.query.filter_by(email=email).first()
        
        if user_exists or doctor_exists:
            flash("A user with this email already exists.", "danger")
            return redirect(url_for('admin_manage_doctors'))

        # 1. Create the User login for the doctor
        new_user_login = User(
            username=name,
            email=email,
            password=generate_password_hash(password),
            usertype='Doctor'
        )
        db.session.add(new_user_login)
        
        # 2. Create the Doctor profile
        new_doctor_profile = Doctors(
            doctorname=name,
            email=email,
            dept=dept
        )
        db.session.add(new_doctor_profile)
        
        # --- NEW LOGIC: Create default availability ---
        # We must commit here so new_doctor_profile gets its 'did' (ID)
        db.session.commit()
        
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days_of_week:
            default_availability = DoctorAvailability(
                day_name=day,
                start_time=None, # None means unavailable
                end_time=None,
                doctor_id=new_doctor_profile.did
            )
            db.session.add(default_availability)
            
        # Commit the new availability records
        db.session.commit()
        # --- END OF NEW LOGIC ---
        
        flash("Doctor profile and default schedule created successfully.", "success")
        return redirect(url_for('admin_manage_doctors'))

    # GET request: Show the list of doctors
    all_doctors = Doctors.query.all()
    return render_template('admin_manage_doctors.html', doctors=all_doctors)

@app.route('/admin/doctors/edit/<int:did>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_doctor(did):
    doctor = Doctors.query.get_or_404(did)
    user = User.query.filter_by(email=doctor.email).first()

    if request.method == 'POST':
        # Update Doctor profile
        doctor.doctorname = request.form.get('doctorname')
        doctor.email = request.form.get('email')
        doctor.dept = request.form.get('dept')
        
        # Update User login (if email changed)
        if user:
            user.username = request.form.get('doctorname')
            user.email = request.form.get('email')
            
            # Optionally reset password
            new_password = request.form.get('password')
            if new_password:
                user.password = generate_password_hash(new_password)
                
        db.session.commit()
        flash("Doctor profile updated successfully.", "success")
        return redirect(url_for('admin_manage_doctors'))

    # GET request: Show the edit form
    return render_template('admin_edit_doctor.html', doctor=doctor)


@app.route('/admin/doctors/delete/<int:did>')
@login_required
@admin_required
def admin_delete_doctor(did):
    doctor = Doctors.query.get_or_404(did)
    user = User.query.filter_by(email=doctor.email).first()

    # --- Important: Check for dependencies ---
    # We must check if this doctor has appointments.
    # A simple delete is better than a cascade for this project.
    appointments = Appointment.query.filter_by(doctor_id=did).first()
    if appointments:
        flash("Cannot delete doctor. They are assigned to one or more appointments. Please re-assign appointments first.", "danger")
        return redirect(url_for('admin_manage_doctors'))

    # If no appointments, proceed with deletion
    if user:
        db.session.delete(user) # Delete the login
    db.session.delete(doctor)   # Delete the profile
    db.session.commit()
    
    flash("Doctor profile and login deleted successfully.", "success")
    return redirect(url_for('admin_manage_doctors'))


# --- RAMMIDOC: ensure admin user exists programmatically ---

# ... (keep your ensure_admin function exactly as it is) ...
def ensure_admin():
    try:
        admin = User.query.filter_by(usertype='Admin').first()
    except Exception:
        admin = None
    if not admin:
        try:
            admin = User(username='admin', usertype='Admin', email='admin@rammidoc.local', password=generate_password_hash('Admin@123'))
            db.session.add(admin)
            db.session.commit()
            print('[RAMMIDOC] Created default admin: admin@rammidoc.local / Admin@123')
        except Exception as e:
            print('[RAMMIDOC] Could not create admin automatically:', e)



@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # --- Get Statistics (Core Requirement) ---
    stats = {
        'doctors': Doctors.query.count(),
        'patients': User.query.filter_by(usertype='Patient').count(),
        'appointments': Appointment.query.count()
    }
    
    # --- Get All Appointments (Core Requirement) ---
    all_appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    return render_template('admin_dashboard.html', stats=stats, all_appointments=all_appointments)


@app.route('/admin/appointments')
@login_required
@admin_required
def admin_appointments():
    # This route just shows the full list of appointments
    # For now, we'll just redirect to the dashboard which already has the list
    return redirect(url_for('admin_dashboard'))


# This is the standard way to run a Flask app
if __name__ == '__main__':
    # We must be "inside" the app to run db commands
    with app.app_context():
        db.create_all()
        ensure_admin()  # This will also run your admin-creation function
    
    # This starts the web server
    app.run(debug=True)

