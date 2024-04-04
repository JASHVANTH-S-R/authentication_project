from flask import Flask, render_template, request, redirect, session, send_file
from flask import send_from_directory
import csv
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'

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
        return render_template('login.html', error=True)

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
            return render_template('success1.html', section_name=section_name)
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

@app.route('/profile')
def profile():
    # Check if user is logged in
    if 'email' not in session:
        return redirect('/')

    # Fetch user data from the backend (you may adjust this according to your data model)
    email = session['email']
    users = read_users('users.csv')
    user_role = users.get(email, {}).get('role')  # Fetch user's role from the user dictionary

    # Render the profile template with dynamic data
    return render_template('profile.html', email=email, role=user_role)

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('role', None)
    session.pop('section_index', None)
    return redirect('/')

@app.route('/success')
def success():
    if 'email' not in session:
        return redirect('/')
    
    return render_template('success1.html')

# Route for uploading files
@app.route('/upload', methods=['POST'])
def upload():
    # Check if the user is an admin
    if session.get('role') != 'Admin':
        return "You do not have permission to upload files."

    # Handle file upload
    uploaded_file = request.files['file']
    if uploaded_file:
        filename = secure_filename(uploaded_file.filename)
        # Save the file to the server
        uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # Add the file to the files.csv with default permission 'read'
        files = read_files()
        files.append({'name': filename, 'permission': 'read'})
        write_files(files)
        return redirect('/dashboard')
    else:
        return "No file selected for upload."

# Route for transferring files
@app.route('/transfer', methods=['POST'])
def transfer():
    # Check if the user has permission to transfer files
    if session.get('role') != 'Admin':
        return "You do not have permission to transfer files."
    
    # Handle file transfer
    recipient_email = request.form['recipient_email']
    filename = request.form['filename']
    permission = request.form['permission']
    
    # Update permission for the file in files.csv
    files = read_files()
    file = next((f for f in files if f['name'] == filename), None)
    if file:
        file['permission'] = permission
        write_files(files)
        return redirect('/dashboard')
    else:
        return "File not found."

# Function to read files and permissions from files.csv
def read_files():
    files = []
    with open('files.csv', 'r', newline='', encoding='utf-8-sig') as file_csv:
        reader = csv.DictReader(file_csv)
        for row in reader:
            files.append({'name': row['name'], 'permission': row['permission']})
    return files

# Function to write files and permissions to files.csv
def write_files(files):
    with open('files.csv', 'w', newline='', encoding='utf-8-sig') as file_csv:
        fieldnames = ['name', 'permission']
        writer = csv.DictWriter(file_csv, fieldnames=fieldnames)
        writer.writeheader()
        for file in files:
            writer.writerow(file)

# Route for managing permissions
@app.route('/manage_permissions', methods=['POST'])
def manage_permissions():
    if 'email' not in session:
        return redirect('/')

    try:
        # Read the form data
        updated_permissions = {}
        for filename, permission in request.form.items():
            updated_permissions[filename] = permission

        # Update permissions in the CSV file
        with open('files.csv', 'r+', newline='', encoding='utf-8-sig') as file_csv:
            reader = csv.DictReader(file_csv)
            rows = list(reader)
            file_csv.seek(0)
            writer = csv.DictWriter(file_csv, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in rows:
                row['permission'] = updated_permissions.get(row['name'], row['permission'])
                writer.writerow(row)

        return redirect('/dashboard')
    except Exception as e:
        print(f"Error updating permissions: {e}")
        return redirect('/dashboard?error=permissions_update_failed')

# Route for downloading files
@app.route('/download/<path:filename>')
def download(filename):
    # Check if the user has permission to download the file
    files = read_files()
    file = next((f for f in files if f['name'] == filename), None)
    if file and file['permission'] in ['read', 'edit']:
        # Replace 'uploads' with the directory where your files are stored
        return send_from_directory('uploads', filename, as_attachment=True)
    else:
        return "You do not have permission to download this file."

if __name__ == "__main__":
    app.run(debug=True,port=5000)
