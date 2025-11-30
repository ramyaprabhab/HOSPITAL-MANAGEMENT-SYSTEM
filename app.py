from flask import Flask,render_template,redirect,url_for,flash,request
from config import Config
from models import db,User,Appointment,Treatment
from forms import LoginForm,RegisterForm,DoctorForm,AppointmentForm,ProfileForm,AvailabilityForm
from flask_login import LoginManager,login_user,logout_user,current_user,login_required
from datetime import date,datetime
from werkzeug.security import generate_password_hash,check_password_hash

app=Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view='login'
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def create_admin_if_needed():
    admin_email='admin@gmail.com'
    if not User.query.filter_by(email=admin_email).first():
        admin=User(email=admin_email, name='Admin', role='admin',password=generate_password_hash('AdminPass123'))
        db.session.add(admin)
        db.session.commit()
        print(f"Admin Created: {admin_email} / AdminPass123")
with app.app_context():
    db.create_all()
    create_admin_if_needed()
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    form=RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered', 'warning')
            return redirect(url_for('register'))
        user=User(email=form.email.data, name=form.name.data, role='patient', 
                    contact=form.contact.data, age=form.age.data,
                    password=generate_password_hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

#dsbd pg
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return admin_dashboard()
    elif current_user.role == 'doctor':
        return doctor_dashboard()
    else:
        return patient_dashboard()

def admin_dashboard():
    doc_count = User.query.filter_by(role='doctor').count()
    pat_count = User.query.filter_by(role='patient').count()
    appt_count = Appointment.query.count()
    return render_template('admin_dashboard.html', doc_count=doc_count, pat_count=pat_count, appt_count=appt_count)

def doctor_dashboard():
    today = date.today()
    upcoming = Appointment.query.filter(
        Appointment.doctor_id == current_user.id, 
        Appointment.date >= today
    ).order_by(Appointment.date, Appointment.time).all()
    patient_ids = [a.patient_id for a in current_user.appointments_as_doctor]
    my_patients = User.query.filter(User.id.in_(patient_ids)).all() if patient_ids else []
    
    return render_template('doctor_dashboard.html', upcoming=upcoming, patients=my_patients)

def patient_dashboard():
    doctors = User.query.filter_by(role='doctor').all()
    specializations = list(set([d.specialization for d in doctors if d.specialization]))
    
    upcoming = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.date >= date.today()
    ).order_by(Appointment.date).all()

    history = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.date.desc()).all()
    return render_template('patient_dashboard.html', specializations=specializations, upcoming=upcoming, history=history)
#patient's dshbd
@app.route('/doctors/<spec>')
@login_required
def doctors_by_spec(spec):
    doctors = User.query.filter_by(role='doctor', specialization=spec).all()
    return render_template('doctors_list.html', doctors=doctors, spec=spec)

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if current_user.role != 'patient': return redirect(url_for('dashboard'))
    form = AppointmentForm()
    doctors = User.query.filter_by(role='doctor').all()
    form.doctor.choices = [(d.id, f"{d.name} ({d.specialization})") for d in doctors]
    #the 2* booking thingy fr preventing the dble bokin for the dr apmt
    if form.validate_on_submit():
        exists=Appointment.query.filter_by(doctor_id=form.doctor.data, date=form.date.data, time=form.time.data).first()
        if exists and exists.status != 'Cancelled':
            flash('Doctor is already booked at this time.', 'danger')
        else:
            appt=Appointment(patient_id=current_user.id, doctor_id=form.doctor.data, 
                               date=form.date.data, time=form.time.data, status='Booked')
            db.session.add(appt)
            db.session.commit()
            flash('Appointment Booked!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('book.html', form=form)
#pf 
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name=form.name.data
        current_user.contact=form.contact.data
        if current_user.role=='doctor': current_user.specialization=form.specialization.data
        if current_user.role=='patient': current_user.age=form.age.data
        if form.password.data:
            current_user.password=generate_password_hash(form.password.data)
        db.session.commit()
        flash('Profile Updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('profile.html', form=form)
    #dr avail thingy
@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
def update_availability():
    if current_user.role != 'doctor': return redirect(url_for('dashboard'))
    form=AvailabilityForm()
    if request.method=='GET':
        form.notes.data=current_user.availability_notes
    if form.validate_on_submit():
        current_user.availability_notes = form.notes.data
        db.session.commit()
        flash('Availability updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('availability.html', form=form)
#tremnts
@app.route('/treatment/<int:appt_id>', methods=['GET', 'POST'])
@login_required
def treatment(appt_id):
    appt=Appointment.query.get_or_404(appt_id)
    if request.method=='POST':
        diagnosis=request.form.get('diagnosis')
        prescription=request.form.get('prescription')
        notes=request.form.get('notes')
        
        tr=Treatment.query.filter_by(appointment_id=appt.id).first()
        if not tr:
            tr= Treatment(appointment_id=appt.id)
            db.session.add(tr)
            
        tr.diagnosis=diagnosis
        tr.prescription=prescription
        tr.notes=notes
        appt.status='Completed'
        db.session.commit()
        flash('Treatment saved & Appointment Completed','success')
        return redirect(url_for('dashboard'))
     
    existing=Treatment.query.filter_by(appointment_id=appt.id).first()
    return render_template('treatment.html',appt=appt,existing=existing)

@app.route('/history/<int:patient_id>')
@login_required
def view_history(patient_id):
    patient=User.query.get_or_404(patient_id)
    history=Appointment.query.filter_by(patient_id=patient.id, status='Completed').all()
    return render_template('history.html', patient=patient, history=history)
#aptmns users for d admin user thing
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin': return redirect(url_for('dashboard'))
    q=request.args.get('q')
    if q:
        users= User.query.filter(User.name.contains(q)|User.email.contains(q)|User.contact.contains(q)).all()
    else:
        users= User.query.filter(User.role != 'admin').all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/add_doctor',methods=['GET', 'POST'])
@login_required
def admin_add_doctor():
    if current_user.role!='admin': return redirect(url_for('dashboard'))
    form=DoctorForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email exists','warning')
        else:
            doc= User(email=form.email.data,name=form.name.data,role='doctor', 
                       specialization=form.specialization.data, contact=form.contact.data,
                       password=generate_password_hash('doctorpass'))
            db.session.add(doc)
            db.session.commit()
            flash('Doctor added', 'success')
            return redirect(url_for('admin_users'))
    return render_template('admin_add_doctor.html', form=form)

@app.route('/admin/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(id):
    if current_user.role!='admin': return redirect(url_for('dashboard'))
    user= User.query.get_or_404(id)
    if request.method=='POST':
        user.name=request.form.get('name')
        user.contact=request.form.get('contact')
        if user.role=='doctor':user.specialization=request.form.get('specialization')
        if user.role=='patient':user.age=request.form.get('age')
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin_edit_user.html', user=user)
#apintmts funct
@app.route('/admin/appointments')
@login_required
def admin_appointments():
    if current_user.role!='admin': return redirect(url_for('dashboard'))
    appts=Appointment.query.order_by(Appointment.date.desc()).all()
    return render_template('admin_appointments.html', appts=appts)

@app.route('/appt/cancel/<int:id>', methods=['POST'])
@login_required
def cancel_appt(id):
    appt = Appointment.query.get_or_404(id)
    if current_user.role=='patient' and appt.patient_id != current_user.id:
        return "Unauthorized", 403
    appt.status='Cancelled'
    db.session.commit()
    flash('Appointment Cancelled', 'info')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/admin/delete_user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != 'admin': return redirect(url_for('dashboard'))
    user=User.query.get_or_404(id)
    Appointment.query.filter((Appointment.doctor_id==id) | (Appointment.patient_id==id)).delete()
    db.session.delete(user)
    db.session.commit()
    flash('User deleted', 'success')
    return redirect(url_for('admin_users'))

if __name__=='__main__':
    app.run(debug=True, port=5000)
