
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