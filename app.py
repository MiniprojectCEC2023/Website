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

mode='local'

if mode=='local':
    app = Flask(__name__)
    app.secret_key = 'your_secret_key_here'
    app.config['MONGO_URI'] = 'mongodb://localhost:27017/admin'
    mongo = PyMongo(app)
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017") 
    db = client['admin']
else:
    app = Flask(__name__)
    app.secret_key = 'your_secret_key_here'
    app.config['MONGO_URI'] = 'mongodb://localhost:27017/myapp'
    mongo = PyMongo(app)
    # Connect to MongoDB
    client = MongoClient("mongodb+srv://shiban:hqwaSJns8vkQVVtk@cluster0.6dhrc7h.mongodb.net/test") 
    db = client['myapp']


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
        students_cursor = db.student.find({}, {'name': 1, 'email': 1, 'register_number': 1, 'semester': 1})
        students = list(students_cursor)
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
        student = db.student.find_one({'register_number': register_number})
        if request.method == 'POST':
            semester = request.form['semester']
            db.student.update_one({'register_number': register_number}, {'$set': {'semester': semester}})
            db.library.update_many({'register_number': register_number}, {'$set': {'semester': semester}})
            db.bus.update_many({'register_number': register_number}, {'$set': {'semester': semester}})
            db.bus.update_one({'register_number': register_number}, {'$set': {'fee_paid': '0'}})
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
            db.library.delete_many({'register_number': register_number})
            db.bus.delete_many({'register_number': register_number})
            db.book_loans.delete_many({'register_number': register_number})
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


#Route to add students to library
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
                'max_book': 4,
                'books_taken':0
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


#Route to view library students
@app.route('/reg_lib')
def reg_lib():
    if session.get('username') == 'library':
        students = db.library.find({}, {'name': 1, 'email': 1, 'register_number': 1, 'semester': 1,'books_taken':1})
        return render_template('librarian/reg_lib.html', students=students)
    else:
        error = 'You need to log in as librarian first.'
        flash(error)
        logging.warning(error)
        return redirect('/librarian-login')


# Route to view each library profile of students
@app.route('/lib_profile/<string:register_number>')
def lib_profile(register_number):
    # Get student's record from the database
    student = db.library.find_one({'register_number': register_number})
    # Check if student exists
    if not student:
        flash('Student not found.')
        logging.warning('Student not found.')
        return redirect('/')
      # Get all books that the student has borrowed
    books = list(db.books.find())
    book_loans = list(db.book_loans.find({'register_number': student['register_number']}))
    # Render the template with the student's information and book details
    return render_template('librarian/lib_profile.html', student=student,books=books,book_loans=book_loans)


import datetime
@app.route('/borrow/<string:register_number>', methods=['POST'])
def borrow(register_number):
    # Get the student ID and book ID from the request data
    title = request.form.get('title')
    # Find the student and book in the respective collections
    student = db.library.find_one({"register_number": register_number})
    book = db.books.find_one({"title": title})
    # If the student and book exist and the book has available copies, create a loan record
    if student and book and book['copies_available'] > 0 and student['max_book'] > 0:
        # Decrement the "copies_available" field for the book in the "books" collection
        db.books.update_one({"title": title}, {"$inc": {"copies_available": -1}})
        # Insert a loan record into the "book loans" collection with an automatically generated loan ID,
        # the student ID, the book ID, the loan date (set to the current date), and the return date (set to 6 months from now)
        db.book_loans.insert_one({
            "loan_id": db.book_loans.count_documents({}) + 1,
            "register_number": student['register_number'],
            "title": book['title'],
            "loan_date": datetime.datetime.utcnow(),
            "return_date": datetime.datetime.utcnow() + datetime.timedelta(days=180)
        })
        db.library.update_one({"register_number": register_number}, {"$inc": {"books_taken": 1}})
        db.library.update_one({"register_number": register_number}, {"$inc": {"max_book": -1}})
        return "Book borrowed successfully!"
    else:
        return "Book not available for borrowing."


@app.route('/return/<string:register_number>', methods=['POST'])
def return_book(register_number):
    # Get the book title from the request data
    title = request.form.get('title')
    # Find the student and book in the respective collections
    student = db.library.find_one({"register_number": register_number})
    book = db.books.find_one({"title": title})
    loan = db.book_loans.find_one({"register_number": register_number, "title": title, "returned_date": None})
    # If the student, book, and loan exist, update the loan record with the returned date and increment the "copies_available" field for the book in the "books" collection
    if student and book and loan:
        db.book_loans.delete_one({"_id": loan["_id"]})
        db.books.update_one({"title": title}, {"$inc": {"copies_available": 1}})
        db.library.update_one({"register_number": register_number}, {"$inc": {"books_taken": -1}})
        db.library.update_one({"register_number": register_number}, {"$inc": {"max_book": 1}})
        return "Book returned successfully!"
    else:
        return "Unable to return book. Please check the book title and ensure that the book is currently on loan."




# Route to delete library profile
@app.route('/delete-std-lib/<register_number>', methods=['GET'])
def delete_std_lib(register_number):
    if session.get('username') == 'library':
        student = db.library.find_one({'register_number': register_number})
        if student:
            books_taken = student.get('books_taken', 0)
            if books_taken == 0:
                db.library.delete_one({'register_number': register_number})
                db.student.update_one({'register_number': register_number}, {'$set': {'added_to_library': 0}})
                flash('Student record deleted successfully')
            else:
                flash('Cannot delete student record as they have books taken from the library')
            return redirect('/reg_lib')
        else:
            error = 'Student record not found'
            flash(error)
            logging.warning(error)
            return redirect('/reg_lib')
    else:
        error = 'You need to log in as librarian first.'
        flash(error)
        logging.warning(error)
        return redirect('/librarian-login')



#Route to open scanner
@app.route('/qrlib')
def qrlib():
    return render_template('librarian/scan_qr_code.html')


#Route to view library profile after scanning
@app.route('/lib_profile_qr', methods=['GET'])
def lib_profile_qr():
    # Get the QR code data from the URL parameters
    data = request.args.get('data')
    # Split the data string into individual data elements
    data_elements = data.split(',')
    # Extract the register number from the data
    register_number = ''
    for element in data_elements:
        if 'Register Number:' in element:
            register_number = element.split(': ')[1]
            break
    # Find the document in the 'library' collection with the matching register number
    student = db.library.find_one({'register_number': register_number})
    # If the student variable is None, render an error message
    if student is None:
        return render_template('librarian/invalid_qr.html')  
    books = list(db.books.find())
    book_loans = list(db.book_loans.find({'register_number': student['register_number']}))
    # Render a template that displays the document
    return render_template('librarian/lib_profile_scaned.html', student=student,books=books,book_loans=book_loans)



################################################################
#----------------------------OFFICE----------------------------#
################################################################


#Route to get office login page and login to office dashboard
@app.route('/college-office-login', methods=['GET', 'POST'])
def college_office_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'office' and password == 'o1234':
            session['username'] = username
            return redirect('/college-office-dashboard')
        else:
            error = 'Invalid username or password'
            flash(error)
            logging.warning(error)
            return render_template('office/college-office-login.html')
    else:
        return render_template('office/college-office-login.html')


#Route to get office dashboard
@app.route('/college-office-dashboard')
def college_office_dashboard():
    if session.get('username') == 'office':
        return render_template('office/college-office-dashboard.html')
    else:
        error = 'You need to log in as college office first.'
        flash(error)
        logging.warning(error)
        return redirect('/college-office-login')


# Route for viewing students who have not registered for college bus by office
@app.route('/view-std-bus')
def view_std_bus():
    if session.get('username') == 'office':
        students = db.student.find({"added_to_bus": 0}, {"name": 1, "email": 1, "register_number": 1, "semester": 1})
        return render_template('office/view-std-bus.html', students=students)
    else:
        error = 'You need to log in as office first.'
        flash(error)
        logging.warning(error)
        return redirect('/college-office-login')


#Route to add students to bus facilities
@app.route('/add_bus/<register_number>', methods=['GET'])
def add_to_bus(register_number):
    if session.get('username') == 'office':
        student = db.student.find_one({'register_number': register_number})
        if student:
            bus_record = {
                'name': student['name'],
                'email': student['email'],
                'semester': student['semester'],
                'branch': student['branch'],
                'register_number': student['register_number'],
                'qr_code': student['qr_code'],
                'fee_paid': 0,
                'route_name':'',
                'fee_per_semester': 0
            }
            db.bus.insert_one(bus_record)
            db.student.update_one({'register_number': register_number}, {'$set': {'added_to_bus': 1}})
            flash('Student record added to office successfully')
            return redirect('/view-std-bus')
        else:
            error = 'Student not found'
            flash(error)
            logging.warning(error)
            return redirect('/view-std-bus')
    else:
        error = 'You need to log in as office first.'
        flash(error)
        logging.warning(error)
        return redirect('/college-office-login')


#Route to view bus students
@app.route('/reg_bus')
def reg_bus():
    if session.get('username') == 'office':
        students = db.bus.find({}, {'name': 1, 'email': 1, 'register_number': 1, 'semester': 1, 'fee_paid': 1})
        return render_template('office/reg_bus.html', students=students)
    else:
        error = 'You need to log in as office first.'
        flash(error)
        logging.warning(error)
        return redirect('/college-office-login')


#Route to view bus profile of students
@app.route('/bus_profile/<string:register_number>')
def bus_profile(register_number):
    # Get student's record from the database
    student = db.bus.find_one({'register_number': register_number})
    # Check if student exists
    if not student:
        flash('Student not found.')
        logging.warning('Student not found.')
        return redirect('/')
    # Render the template with the student's information and book details
    return render_template('office/bus_profile.html', student=student)


#Route to update fee status of student
@app.route('/update_infobus/<string:register_number>', methods=['POST'])
def update_infobus(register_number):
    fee_paid = request.form.get('fee_paid')
    # Update the student information in your database or data structure
    student = db.bus.find_one({'register_number': register_number})
    db.bus.update_one({'register_number': register_number}, {'$set': {'fee_paid': fee_paid}})
    return render_template('office/bus_profile.html', student=student)


#Route to update route of bus
@app.route('/update_bus_route/<register_number>', methods=['POST'])
def update_bus_route(register_number):
  # Update the route information in your database or data structure
  route_name = request.form.get('route_name')
  student = db.bus.find_one({"register_number": register_number})
  if not student:
    return "Student not found" 
  route = db.routes.find_one({"route_name": route_name})
  if not route:
    return "Route not found"
  db.bus.update_one({"register_number": register_number}, {"$set": {"route_name": route_name, "fee_per_semester": route["fee_per_semester"]}})
  db.bus.update_one({'register_number': register_number}, {'$set': {'fee_paid': '0'}})
  return render_template('office/bus_profile.html', student=student)


#Route to delete a bus student 
@app.route('/delete-std-bus/<register_number>', methods=['GET'])
def delete_std_bus(register_number):
    if session.get('username') == 'office':
        student = db.bus.find_one({'register_number': register_number})
        if student:
            db.bus.delete_one({'register_number': register_number})
            db.student.update_one({'register_number': register_number}, {'$set': {'added_to_bus': 0}})
            flash('Student record deleted successfully')
            return redirect('/reg_bus')
        else:
            error = 'Student record not found'
            flash(error)
            logging.warning(error)
            return redirect('/reg_bus')
    else:
        error = 'You need to log in as librarian first.'
        flash(error)
        logging.warning(error)
        return redirect('/librarian-login')
#Route to open scanner
@app.route('/qrbus')
def qrbus():
    return render_template('office/scan_qr_code.html')


#Route to view bus profile of students after scanning
@app.route('/bus_profile_qr', methods=['GET'])
def bus_profile_qr():
    # Get the QR code data from the URL parameters
    data = request.args.get('data')
    # Split the data string into individual data elements
    data_elements = data.split(',')
    # Extract the register number from the data
    register_number = ''
    for element in data_elements:
        if 'Register Number:' in element:
            register_number = element.split(': ')[1]
            break
    # Find the document in the 'bus' collection with the matching register number
    student = db.bus.find_one({'register_number': register_number})
    # If the student variable is None, render an error message
    if student is None:
        return render_template('office/invalid_qr.html')
    # Render a template that displays the document
    return render_template('office/bus_profile_scaned.html', student=student)



################################################################
#----------------------------LOGOUT----------------------------#
################################################################


#Route to logout  
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