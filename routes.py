# modify tables names
from BrainBoost.models import User, HistoryRecord, Flashcard
from flask import render_template, url_for, flash, redirect, request, jsonify, session
from BrainBoost.forms import RegistrationForm, LoginForm, UpdateProfileForm
from BrainBoost import app, bcrypt, db
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from flask_login import (
    login_required,
    login_user,
    current_user,
    logout_user,
    login_required,
)
from wtforms.validators import InputRequired  # , FileAllowed
from wtforms import ValidationError
from werkzeug.utils import secure_filename
import secrets
# from PIL import Image
import os
from sqlalchemy import func, desc
from BrainBoost.Model import PDFProcessor

global idCounter
idCounter = 1

global flashcardIdCounter
flashcardIdCounter = 1

global fileIdCounter
fileIdCounter = 1

# get flashcards interface link
'''def get_link(file_id):
    file = next((f for f in files if f['id'] == file_id), None)
    if file:
        link = url_for('retrieve_file_data', file_id=file_id, _external=True)
        return jsonify({"link": link})
    else:
        return jsonify({"error": "File not found"}), 404
# retrieve flashcrds
@app.route('/retrieve_file_data/<int:file_id>')
def retrieve_file_data(file_id):
    # Dummy function to retrieve file data
    # Replace this with your actual logic to retrieve file data
    file = next((f for f in files if f['id'] == file_id), None)
    if file:
        return f"Data for {file['name']}"
    else:
        return "File not found", 404
    '''


# route decorator
@app.route("/")
@app.route("/main")
def main():
    return render_template("index.html")


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# signup
@app.route("/signUp", methods=["GET", "POST"])
def signUp():
    """Sign up"""
    try:
        # global idCounter
        # if current_user.is_authenticated:
        # return redirect(url_for("upload"))

        form = RegistrationForm()
        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
                "utf-8"
            )
            user = User.query.order_by(desc(User.id)).first()
            new_user = User(
                id=user.id + 1 if user.id else 1,
                username=form.username.data,
                email=form.email.data,
                password=hashed_password,
            )
            db.session.add(new_user)
            db.session.commit()

            flash(f"Account created successfully for {form.username.data}", "success")
            return redirect(url_for("login"))
        return render_template("sing-up-interface.html", title="signUp", form=form)
    except Exception as e:
        # Handle the exception here
        flash(f"An error occurred: {str(e)}", "error")


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# login
@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        # if current_user.is_authenticated:
        #     return redirect(url_for("upload"))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                flash("You have been logged in!", "success")
                return redirect(next_page) if next_page else redirect(url_for("upload"))
            else:
                flash("Login Unsuccessful. Please check credentials", "danger")
        return render_template("log-in-interface.html", title="Login", form=form)
    except Exception as e:
        # Handle the exception here
        flash(f"An error occurred: {str(e)}", "error")


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# logout and dashboard
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", title="Dashboard")


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# upload file

def allowed_file(form, field):
    if not '.' in field.data.filename or \
            field.data.filename.rsplit('.', 1)[1].lower() not in app.config['ALLOWED_EXTENSIONS']:
        raise ValidationError('Only PDF files are allowed.')


class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[
        InputRequired(),
        allowed_file
    ])
    submit = SubmitField("Upload File")


@app.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    try:
        form = UploadFileForm()
        if form.validate_on_submit():
            file = form.file.data  # First grab the file
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            global fileIdCounter
            history_record = HistoryRecord.query.order_by(desc(HistoryRecord.file_id)).first()
            new_history_record = HistoryRecord(file_id=history_record.file_id + 1,
                                               file_name=filename,
                                               user_id=current_user.id)
            db.session.add(new_history_record)
            db.session.commit()

            global flashcardIdCounter

            ## file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            ## file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            ## file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))  # Then save the file
            ## file_path = os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(file.filename))
            # return "File has been uploaded."

            # (Jetana) Calling the class and functions in model
            pdf_processor = PDFProcessor(file_path)
            # Perform text preprocessing
            sentences = pdf_processor.TextPreprocessing()

            questions = pdf_processor.QuestionGeneration(sentences)
            correct_answers = pdf_processor.AnswerGeneration(sentences, questions)
            distractors = pdf_processor.GenerateDistractors(sentences, questions, correct_answers)
            # Loop through all the data and create flashcards
            for index, question in enumerate(questions):
                # Initialize a new Flashcard object
                flashcard = Flashcard(
                    # flashcard_id=index + 1,
                    flashcard_id=flashcardIdCounter,
                    question=question,
                    file_id=fileIdCounter
                )
                # Add the flashcard to the session
                db.session.add(flashcard)

                flashcardIdCounter = flashcardIdCounter + 1
                # Set the correct answer for this flashcard if available
                if index < len(correct_answers):
                    flashcard.right_answer = correct_answers[index]
                # Set choices for this flashcard if available
                if index in distractors:
                    choices = distractors[index]
                    if len(choices) >= 4:
                        flashcard.choice1 = choices[0]
                        flashcard.choice2 = choices[1]
                        flashcard.choice3 = choices[2]
                        flashcard.choice4 = choices[3]
                # Commit changes after each flashcard
                db.session.commit()
            # ------------------------------------------------------------------------------------------
            # Clean up the uploaded file

            # session['fileId'] =fileIdCounter
            fileIdCounter = fileIdCounter + 1
            os.remove(file_path)

            return redirect(url_for("flashcards"))
        return render_template('upload-interface.html', form=form)

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# edit account
# 2222222222222222222222222222222222222222222222222222222222222222222222delete button
@app.route("/profile", methods=["GET", "POST"])
# @login_required
def profile():
    try:
        profile_form = UpdateProfileForm()
        if profile_form.validate_on_submit():
            if "delete" in request.form:
                # Delete the user's account
                db.session.delete(current_user)
                db.session.commit()
                flash("Your account has been deleted.", "success")
                return redirect(url_for("main"))
            else:
                # Update the user's profile
                current_user.username = profile_form.username.data
                current_user.email = profile_form.email.data
                hashed_password = bcrypt.generate_password_hash(profile_form.password.data).decode('utf-8')
                current_user.password = hashed_password
                db.session.commit()
                flash("Your profile has been updated", "success")
                return redirect(url_for("profile"))
        elif request.method == "GET":
            profile_form.username.data = current_user.username
            profile_form.email.data = current_user.email

        return render_template(
            "user-info-interface.html",
            title="userProfile",
            profile_form=profile_form

        )
    except Exception as e:
        # Handle the exception here
        flash(f"An error occurred: {str(e)}", "error")


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

@app.route('/flashcards')
def flashcards():
    # fileId = session.get('fileId')
    flashcards = Flashcard.query.filter_by(file_id=1).all()
    return render_template("flashcard-interface.html", flashcard=flashcards)


@app.route('/update_answer/<int:flashcard_id>/<int:saved_answer>', methods=['POST'])
def update_answer(flashcard_id, saved_answer):
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    flashcard.saved_answer = bool(saved_answer)
    db.session.commit()
    return '', 204


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
@app.route('/overview')
def overview():
    flashcards = Flashcard.query.all()

    return render_template("overview-interface.html", flashcards=flashcards)


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

@app.route('/viewFlashcards')
def viewFlashcards():
    flashcards = Flashcard.query.all()
    return render_template("view-flashcards-interface.html", flashcards=flashcards)


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
@app.route('/viewIncorrectFlashcards')
def incorrect():
    flashcards = Flashcard.query.filter_by(saved_answer=0).all()
    return render_template("incorrect-flashcards.html", flashcards=flashcards)


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

@app.route('/history', methods=['POST'])
@app.route('/history', methods=['GET', 'POST'])
def history():
    history_records = HistoryRecord.query.all()
    current_user_history_records = db.session.query(
        HistoryRecord,
        func.count(Flashcard.flashcard_id).label('flashcard_count')
    ).join(
        User
    ).join(
        Flashcard
    ).filter(
        User.id == current_user.id
    ).group_by(
        HistoryRecord
    ).all()

    if request.method == 'POST':
        data = request.get_json()
        file_id = data.get('file_id', None)

        if not file_id:
            return jsonify({'message': 'File ID is required'}), 400

        record = HistoryRecord.query.filter_by(file_id=file_id).first()

        if not record:
            return jsonify({'message': 'Record not found'}), 404

        db.session.delete(record)
        db.session.commit()

        return jsonify({'message': 'Record deleted successfully'}), 200

    return render_template("view-history-interface.html", history_records=current_user_history_records)


# ------------------------------------------------------
@app.route('/delete_history/<int:file_id>', methods=['POST'])
def delete_history(file_id):
    record = HistoryRecord.query.get_or_404(file_id)
    # Delete associated flashcards
    Flashcard.query.filter_by(file_id=file_id).delete()
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted successfully', 'success')
    return redirect(url_for('history'))


# ------------------------------------------------------

# 2222222222222222222222222222222222222222222222222222222222222222222222 not working
@app.route('/rename_file/<int:file_id>', methods=['POST'])
def rename_file(file_id):
    data = request.form
    new_file_name = data.get('new_file_name')

    if not new_file_name:
        return jsonify({'message': 'New file name is required'}), 400

    record = HistoryRecord.query.filter_by(file_id=file_id).first()
    if not record:
        return jsonify({'message': 'Record not found'}), 404

    record.file_name = new_file_name
    db.session.commit()

    return jsonify({'message': 'File renamed successfully'}), 200


@app.route('/delete_file_history/<int:file_id>', methods=['POST'])
def delete_file_history(file_id):
    try:
        flashcards = Flashcard.query.filter_by(file_id=file_id).all()
        for flashcard in flashcards:
            db.session.delete(flashcard)
        db.session.commit()
        record = HistoryRecord.query.filter_by(file_id=file_id).first()
        if record:
            db.session.delete(record)
            db.session.commit()
            flash('Record deleted successfully', 'success')
        else:
            flash('Record not found', 'error')

        return redirect(url_for('history'))

    except Exception as e:
        print(f"An error occurred: {str(e)}", "error")


@app.route('/get_all_flashcard/<int:file_id>', methods=['GET'])
def get_all_flashcard(file_id):
    try:
        flashcards = Flashcard.query.filter_by(file_id=file_id).all()
        if flashcards:
            flash('Flashcards retrieved successfully', 'success')
        else:
            flash('No flashcards found for this file ID', 'error')

        return redirect(url_for('history'))

    except Exception as e:
        print(f"An error occurred: {str(e)}", "error")


@app.route('/fetch_all_flashcard', methods=['GET'])
def fetch_all_flashcard():
    try:
        flashcards = Flashcard.query.all()
        if flashcards:
            flash('Flashcards retrieved successfully', 'success')
        else:
            flash('No flashcards found for this file ID', 'error')

        return redirect(url_for('history'))

    except Exception as e:
        print(f"An error occurred: {str(e)}", "error")


# [asma] upload files
# added a flag to check if the file are saved in the database
'''ALLOWED_EXTENSIONS = {'pdf'} # Set of allowed file extensions

class UploadFileForm(FlaskForm):
   file = FileField("File", validators=[InputRequired()])
   submit = SubmitField("Upload File")


@app.route("/upload", methods=['GET','POST'])
@login_required
def upload():
    return render_template("upload-interface.html")

@app.route("/upload_file", methods=['GET','POST'])
@login_required
def upload_file():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return render_template("upload-interface.html"), 400

    file = request.files['file']
    # If the user does not select a file, the browser might
    # submit an empty file part without a filename.
    if file.filename == '':
        return render_template("upload-interface.html"), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'results6.txt')

       ##jetana***************************************************************************************************************************
       ##modify the model name
         # Process the file with TweetCollector
        ##tc = TweetCollector(file_path)
        ##results = tc.process_file(file_path, output_path)
        #print(f"Results count: {len(results)}")

        # Store the results in the global variable to use it in the dashboard
        global uploaded_results
       # uploaded_results = results

        # Clean up the temporary file
        os.remove(file_path)
        # Set a flag in the session to save the results
        ###session['save_results'] = True
    
        ###print("Redirecting to result2")
        ###return jsonify({'success': True, 'redirect': url_for('result2')})
        #return render_template("uploadfile.html")

    else:
        return render_template("upload-interface.html"), 400



def allowed_file(filename):
    return '.' in filename and  filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
##################################################
########################3
'''
'''
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/uploadFile', methods=['GET', 'POST'])

def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        
        file = request.files['file']
        
        if file.filename == '':
            return 'No selected file'
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return 'File uploaded successfully'
        
        return 'Invalid file format'
    
    return render_template("upload-interface.html")
'''
# The upload.html file should contain a form with enctype="multipart/form-data" for file upload.


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
'''
def rename_file():
    data = request.get_json()
    file_id = data.get('file_id')
    new_file_name = data.get('new_file_name')

    # Find the record with the given file_id
    record = HistoryRecord.query.filter_by(file_id=file_id).first()
    if not record:
        return jsonify({"message": "File not found"}), 404

    # Update the file_name with the new_file_name
    record.file_name = new_file_name
    db.session.commit()

    return jsonify({"message": "File renamed successfully"}), 200
'''
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
