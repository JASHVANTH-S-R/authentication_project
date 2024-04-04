from flask import Flask, render_template, jsonify, redirect, url_for, request
import utils
import os
import json 
import shutil
import numpy as np
import csv
import threading
import time
import datetime
import random
import cv2

ACTIVITY_LOG_FILE = 'activity_log.csv'
DATABASE_EFFICIENCY_LOG_FILE = 'database_efficiency_log.csv'


app = Flask(__name__)

selected_images = {}

admin = False
username = None
DOCUMENT_DIR = './documents'
IMG_DIR = './images'

with open(ACTIVITY_LOG_FILE, 'w', newline='') as csvfile:
    fieldnames = ['timestamp', 'username', 'action']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

# Create a CSV file for logging database efficiency
with open(DATABASE_EFFICIENCY_LOG_FILE, 'w', newline='') as csvfile:
    fieldnames = ['timestamp', 'query', 'response_time']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

# Define constants
SAMPLE_QUERIES = ['SELECT * FROM users WHERE username=?', 'SELECT * FROM documents WHERE owner=?']
NUM_SAMPLES = 10  # Number of samples per query

def execute_sample_query(query):
    start_time = time.time()
    # Simulate database query execution with random delay (representative of actual database operation)
    time.sleep(random.uniform(0.1, 0.5))
    response_time = time.time() - start_time

    # Log database efficiency
    log_database_efficiency(query, response_time)


def log_database_efficiency(query, response_time):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(DATABASE_EFFICIENCY_LOG_FILE, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'query', 'response_time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writerow({'timestamp': timestamp, 'query': query, 'response_time': response_time})

with open('data.json', 'r') as jf:
    json_data = json.load(jf)


@app.route('/', methods=['GET', 'POST'])
def facelogin():

    global admin, username

    if request.method == 'POST':
        uploaded_image = request.files['image']
        # Process the uploaded image as needed

        save_path = IMG_DIR+'/image.png'
        uploaded_image.save(save_path)
        exist, admin = utils.detect_faces(save_path)

        admin = 'Admin' if admin else False
        
        if exist:
            return jsonify({"redirect_url": url_for('dashboard')})
    
    return render_template('Facelogin.html')


@app.route('/facesignup', methods=['GET','POST'])
def facesignup():
    if request.method=='POST':
        if 'image' in request.form:
            username =  request.form['username']
            uploaded_file = request.form['image']

            print(uploaded_file)

            adminState = 'admin' == username.split('@')[0].split('.')[-1]
            
            save_path = IMG_DIR+'/image.png'
            uploaded_file.save(save_path)

            if utils.encode_image(username, save_path, adminState):
                if username not in os.listdir(DOCUMENT_DIR):
                    os.mkdir(f'{DOCUMENT_DIR}/{username}')

                return render_template("FaceLogin.html")
            
    return render_template("FaceSignup.html")

def record_video():
    while True:
        # Record video for a certain interval
        utils.record_video()

        # Check for intruders
        intruder_detected = utils.detect_intruder()

        if intruder_detected:
            # Alert intruder
            utils.intruder_alert()

        # Wait for the next recording interval
        time.sleep(utils.RECORDING_INTERVAL)


def log_activity(username, action):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(ACTIVITY_LOG_FILE, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'username', 'action']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writerow({'timestamp': timestamp, 'username': username, 'action': action})

@app.route('/imgsignup', methods=['POST', 'GET'])
def imgsignup():
    global selected_images

    if request.method == 'POST':
        data = request.get_json()

        username = data['username']

        json_data['grid'][username] = list(data['selectedImages'].keys())

        if username.split('@')[0].split('.')[-1]=='admin':
            json_data['roles']['admin'].append(username)
        else:
            json_data['roles']['employee'].append(username)


        with open('data.json', 'w') as jfw:
            json.dump(json_data, jfw)

        if username not in os.listdir(DOCUMENT_DIR):
            os.mkdir(f'{DOCUMENT_DIR}/{username}')


        return jsonify({"redirect_url": url_for('imglogin')})
    
    return render_template('ImageSignup.html')


@app.route('/imglogin', methods=['POST', 'GET'])
def imglogin():

    global admin, username

    if request.method == 'POST':
        data = request.get_json()

        username = data['username']
        
        if json_data['grid'].get(username, False)==list(data['selectedImages'].keys()):
            if username in json_data['roles']['admin']:
                admin = 'Admin'
            else:
                admin = False

            return jsonify({"redirect_url": url_for('dashboard')})
        
    return render_template('Imagelogin.html')


@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():

    global admin, username

    list = utils.get_file_details(f'{DOCUMENT_DIR}/{username}')
    employee_list = json_data['roles']['employee']
    print(employee_list)
    
    if request.method=='POST':

        data = request.get_json()
        file_name = data.get('fileName')
        employee_name = data.get('employee')
        
        doc_path = os.path.join(DOCUMENT_DIR, username, file_name)
        save_path = os.path.join(DOCUMENT_DIR, employee_name, file_name)
        doc_content = utils.read_pdf(doc_path)
        identified_pii, original_entities = utils.identify_pii(doc_content)
        anonymized_text = utils.anonymize_pii(doc_content, identified_pii)
        utils.save_pdf(anonymized_text, save_path)

        return jsonify({'status': 'Assigned Successfully'})

    return render_template('Dashboard.html', list=list , employee_list=employee_list, user="Admin" if admin else "Employee") 

    
@app.route('/fileview', methods=['POST', 'GET'])
def fileview():
    global username

    if request.method=='POST':
        data = request.get_json()
        file_name = data.get('fileName')

        print(file_name)
         # Construct the redirect URL
        ROOT_PATH = 'static/'
        path = f'{DOCUMENT_DIR}/{username}/{file_name}'

        shutil.copy(path, ROOT_PATH)

        redirect_url = url_for('dashboard')

        # Return both the redirect URL and the file path in the JSON response
        return jsonify({"redirect_url": redirect_url, "file_path": ROOT_PATH+file_name})

    file_path = request.args.get('path', '')
    return render_template('FileView.html', path=file_path)


@app.route('/uploadfile' ,methods=['POST','GET'])
def uploadfile():
    if request.method == 'POST':
        uploaded_file = request.files['pdf_doc']
        # print(uploaded_file.filename)
        save_path = f'{DOCUMENT_DIR}/{username}/{uploaded_file.filename}'
        uploaded_file.save(save_path)
        
        return redirect( url_for('dashboard'))
         

if __name__ == "__main__":
    app.run(debug=True,port=5001)
