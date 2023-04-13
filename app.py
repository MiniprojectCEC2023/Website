from flask import Flask, render_template, request, redirect, session, flash, jsonify
from pymongo import MongoClient
import qrcode
from bson.binary import Binary
from io import BytesIO
import PIL
from PIL import Image
from pyzbar.pyzbar import decode
import base64
import logging
import os
import math
from typing import List, Tuple
import binascii
from waitress import serve
from flask_pymongo import PyMongo

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/admin'
mongo = PyMongo(app)
# Connect to MongoDB
""" client = MongoClient("mongodb+srv://shiban:hqwaSJns8vkQVVtk@cluster0.6dhrc7h.mongodb.net/test") 
db = client['myapp'] """
client = MongoClient("mongodb://localhost:27017") 
db = client['admin']



################################################################
#----------------------------INDEX-----------------------------#
################################################################


#INDEX_ROUTE
@app.route('/')
def home():
    return render_template('index.html')


################################################################
#----------------------------ADMIN-----------------------------#
################################################################


#Route to get admin login page and login to admin dashboard
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'a1234':
            session['username'] = username
            return redirect('/admin-dashboard')
        else:
            error = 'Invalid username or password'
            flash(error)
            logging.warning(error)
            return render_template('admin/admin-login.html')
    else:
        return render_template('admin/admin-login.html')

#Route to get admin dashboard
@app.route('/admin-dashboard')
def admin_dashboard():
    if session.get('username') == 'admin':
        return render_template('admin/admin-dashboard.html')
    else:
        error = 'You need to log in as admin first.'
        flash(error)
        logging.warning(error)
        return redirect('/admin-login')

#Route to get register form page
@app.route('/register')
def registers():
    return render_template('admin/register.html')
#Route to submit registration form
@app.route("/register-success", methods=["POST"])
def register():
    if request.method == 'POST':
        name = request.form.get("name")
        email = request.form.get("email")
        register_number = request.form.get("register_number")
        phone = request.form.get("phone")
        address = request.form.get("address")
        dob = request.form.get("dob")
        gender = request.form.get("gender")
        branch = request.form.get("branch")
        semester = request.form.get("semester")

        # Check if all required fields are filled
        if not name or not email or not register_number or not phone or not address or not dob or not gender or not branch or not semester:
            error = 'All fields are required'
            flash(error)
            logging.warning(error)
            return render_template('admin/register.html')

        # Check if email or register number already exists
        result = db.student.find_one({'$or': [{'email': email}, {'register_number': register_number}]})
        if result:
            error = 'Email or register number already exists'
            flash(error)
            logging.warning(error)
            return render_template('admin/register.html')

        # Generate the QR code
        data = f"Name: {name}, Email: {email}, Register Number: {register_number}"
        qr = qrcode.make(data)
        img = BytesIO()
        qr.save(img, "PNG")
        img.seek(0)

        # Insert data and QR code image into the database
        db.student.insert_one({'name': name, 'email': email, 'register_number': register_number, 'phone': phone, 'address': address, 'dob': dob, 'gender': gender, 'branch': branch, 'semester': semester, 'qr_code': Binary(img.read()), 'added_to_library': 0, 'added_to_bus': 0})

        # Save QR code as PNG image in specified folder
        qr_img_path = f"static/qr_codes/{register_number}.png"
        with open(qr_img_path, 'wb') as f:
            f.write(img.getbuffer())

        flash('Registration successful. Please log in.')
        return redirect('/register-success')
    else:
        return render_template('admin/register.html')



#Route to return registration success message
@app.route("/register-success")
def success():
    return "Registration successful!"

# Route for students viewing for admin
@app.route('/view-students')
def view_students():
    if session.get('username') == 'admin':
        students = mongo.db.student.find({}, {'name': 1, 'email': 1, 'register_number': 1, 'semester': 1})
        return render_template('admin/view-students.html', students=students)
    else:
        error = 'You need to log in as admin first.'
        flash(error)
        logging.warning(error)
        return redirect('/admin-login')

# Route to update semester of students by admin
@app.route('/edit-student/<register_number>', methods=['GET', 'POST'])
def edit_student(register_number):
    if session.get('username') == 'admin':
        student = mongo.db.student.find_one({'register_number': register_number})
        if request.method == 'POST':
            semester = request.form['semester']
            mongo.db.student.update_one({'register_number': register_number}, {'$set': {'semester': semester}})
            flash('Student record updated successfully')
            return redirect('/view-students')
        name = student['name']  # get student name from database
        return render_template('admin/edit-student.html', name=name, student=student)
    else:
        error = 'You need to log in as admin first.'
        flash(error)
        logging.warning(error)
        return redirect('/admin-login')

# Route to delete students by admin
@app.route('/delete-student/<register_number>', methods=['GET'])
def delete_student(register_number):
    if session.get('username') == 'admin':
        student = db.student.find_one({'register_number': register_number})
        if student:
            db.student.delete_one({'register_number': register_number})
            flash('Student record deleted successfully')
        else:
            flash('Student record not found')
        return redirect('/view-students')
    else:
        error = 'You need to log in as admin first.'
        flash(error)
        logging.warning(error)
        return redirect('/admin-login')

################################################################
#----------------------------LIBRARY---------------------------#
################################################################

#Route to get librarian login page and login to librarian dashboard
@app.route('/librarian-login', methods=['GET', 'POST'])
def librarian_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'library' and password == 'l1234':
            session['username'] = username
            return redirect('/librarian-dashboard')
        else:
            error = 'Invalid username or password'
            flash(error)
            logging.warning(error)
            return render_template('librarian/librarian-login.html')
    else:
        return render_template('librarian/librarian-login.html')


#Route to get library dashboard
@app.route('/librarian-dashboard')
def librarian_dashboard():
    if session.get('username') == 'library':
        return render_template('librarian/librarian-dashboard.html')
    else:
        error = 'You need to log in as librarian first.'
        flash(error)
        logging.warning(error)
        return redirect('/librarian-login')
    # Route for viewing students who are not added to library by librarian
@app.route('/view-std-lib')
def view_std_lib():
    if session.get('username') == 'library':
        students = db.student.find({'added_to_library': 0})
        return render_template('librarian/view-std-lib.html', students=students)
    else:
        error = 'You need to log in as librarian first.'
        flash(error)
        logging.warning(error)
        return redirect('/librarian-login')

@app.route('/add_lib/<register_number>', methods=['GET'])
def add_to_lib(register_number):
    if session.get('username') == 'library':
        student = db.student.find_one({'register_number': register_number})
        if student:
            library_record = {
                'name': student['name'],
                'email': student['email'],
                'semester': student['semester'],
                'branch': student['branch'],
                'register_number': student['register_number'],
                'qr_code': student['qr_code'],
                'max_book': 4
            }
            db.library.insert_one(library_record)
            db.student.update_one({'register_number': register_number}, {'$set': {'added_to_library': 1}})
            flash('Student record added to library successfully')
            return redirect('/view-std-lib')
        else:
            error = 'Student not found.'
            flash(error)
            logging.warning(error)
            return redirect('/view-student')
    else:
        error = 'You need to log in as librarian first.'
        flash(error)
        logging.warning(error)
        return redirect('/librarian-login')


@app.route('/reg_lib')
def reg_lib():
    if session.get('username') == 'library':
        students = db.library.find({}, {'name': 1, 'email': 1, 'register_number': 1, 'semester': 1})
        return render_template('librarian/reg_lib.html', students=students)
    else:
        error = 'You need to log in as librarian first.'
        flash(error)
        logging.warning(error)
        return redirect('/librarian-login')





################################################################
#----------------------------LOGOUT----------------------------#
################################################################

    
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')

    
mode='dev'
if __name__ == '__main__':
    if mode=='dev':
         app.run(host='0.0.0.0', port=5000,debug=True)
    else:
     serve(app, host='0.0.0.0', port=5000, threads=2, url_prefix="/cec")
