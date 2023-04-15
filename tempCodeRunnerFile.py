#Route to upadate book availability of student
@app.route('/update_info/<string:register_number>', methods=['POST'])
def update_info(register_number):
    books_available = request.form.get('books_available')
    
    # Update the student information in your database
    student = db.library.find_one({'register_number': register_number})
    if student:
        db.library.update_one({'register_number': register_number}, {'$set': {'max_book': int(books_available)}})
        student['max_book'] = int(books_available)
    else:
        return render_template('error.html', message='Student not found.')
    
    return render_template('librarian/lib_profile.html', student=student)