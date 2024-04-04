from flask import Flask, render_template, request, redirect, session, send_file, flash
from flask import send_from_directory
import csv
import random
import os
from werkzeug.utils import secure_filename
import time
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Function to read CSV file and return a dictionary of users
def read_users(file_name):
    with open(file_name, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        users = {row['emailID']: {'userID': row['userID'], 'password': row['Password'], 'role': row['Role']} for row in reader}
    return users

# Function to read CSV file and return a list of questions
def read_questions(file_name):
    with open(file_name, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        questions = list(reader)
    return questions

# Function to select random questions from a list
def select_random_questions(questions_list, num_questions):
    return random.sample(questions_list, num_questions)

# Function to verify user's login credentials
def verify_login(email, password, users):
    if email in users:
        return users[email]['password'] == password, users[email]['role']
    return False, None

# Function to verify user's answer to a question
def verify_answer(question, user_answer):
    correct_answer = question[1]
    return user_answer == correct_answer

# Function to log database query response time
def log_query_response_time(query, response_time):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('database_efficiency_log.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([timestamp, query, response_time])

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    users = read_users('users.csv')
    valid_login, role = verify_login(email, password, users)
    if valid_login:
        session['email'] = email
        session['role'] = role
        session['section_index'] = 0  # Initialize section index
        return redirect('/questions')
    else:
        flash('Invalid email or password', 'error')
        return render_template('login.html')

@app.route('/questions')
def questions():
    if 'email' not in session:
        return redirect('/')
    
    email = session['email']
    users = read_users('users.csv')
    role = session.get('role')  # Retrieve role from session
    section_index = session.get('section_index', 0)
    
    sections = ["Experience", "Identity", "Preference", "Knowledge"]
    
    if section_index < len(sections):
        section_name = sections[section_index]
        session['section_index'] += 1  # Move to the next section for next request
        
        # Read questions from CSV files
        questions_file = f'{section_name.lower()}_questions.csv'
        section_questions = read_questions(questions_file)
        random_section_questions = select_random_questions(section_questions[1:], 3)
        
        return render_template('questions.html', section_name=section_name, section_questions=random_section_questions)
    else:
        session.pop('section_index', None)  # Clear section index for next login
        return redirect('/success')

@app.route('/submit_answers', methods=['POST'])
def submit_answers():
    if 'email' not in session:
        return redirect('/')
    
    email = session['email']
    users = read_users('users.csv')
    role = session.get('role')
    
    section_name = request.form['section_name']
    section_questions = read_questions(f'{section_name.lower()}_questions.csv')
    
    correct_answers = 0
    for question in section_questions[1:]:
        user_answer = request.form.get(question[0])
        if verify_answer(question, user_answer):
            correct_answers += 1
    
    if correct_answers == 3:
        # Check if all sections are completed
        sections = ["Experience", "Identity", "Preference", "Knowledge"]
        if session.get('section_index') == len(sections):
            return render_template('success.html', section_name=section_name)
        else:
            return redirect('/questions')
    else:
        return redirect('/logout')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect('/')

    email = session['email']
    users = read_users('users.csv')
    role = users.get(email, {}).get('role')
    
    if role == 'Admin':
        # Retrieve files and permissions data from CSV
        files = read_files()
        return render_template('admin_dashboard.html', files=files)
    else:
        return render_template('user_dashboard.html')

# Add database efficiency logging to file download route
@app.route('/download/<path:filename>')
def download(filename):
    # Log database query response time
    query = f"SELECT * FROM files WHERE filename='{filename}'"
    start_time = time.time()
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    response_time = time.time() - start_time
    log_query_response_time(query, response_time)

    # Check if the user has permission to download the file
    files = read_files()
    file = next((f for f in files if f['name'] == filename), None)
    if file and file['permission'] in ['read', 'edit']:
        # Replace 'uploads' with the directory where your files are stored
        return send_from_directory('uploads', filename, as_attachment=True)
    else:
        return "You do not have permission to download this file."

# Add database efficiency logging to file upload route
@app.route('/upload', methods=['POST'])
def upload():
    # Log database query response time
    query = "INSERT INTO files (filename, permission) VALUES (?, ?)"
    start_time = time.time()
    
    # Check if the user is an admin
    if session.get('role') != 'Admin':
        return "You do not have permission to upload files."

    # Handle file upload
    uploaded_file = request.files['file']
    if uploaded_file:
        filename = secure_filename(uploaded_file.filename)
        # Save the
