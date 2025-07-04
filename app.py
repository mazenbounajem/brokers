import os
import uuid
from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for,render_template, flash, session
from werkzeug.utils import secure_filename
from pdftoimages import extract_images_from_pdf
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableDict
from werkzeug.security import generate_password_hash, check_password_hash

from createasummarizedvideo import create_video, create_video_from_user_text
import threading
import time
from flask import jsonify

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for flash messages

import base64

def b64encode_filter(data):
    if data is None:
        return ''
    return base64.b64encode(data).decode('utf-8')

app.jinja_env.filters['b64encode'] = b64encode_filter

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER_BASE = 'web_output'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER_BASE, exist_ok=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    login_type = db.Column(db.String(50), nullable=False)  # administrator or broker

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

import json

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_blobs = db.Column(MutableDict.as_mutable(db.PickleType), nullable=True)  # Store image blobs as a dictionary {filename: data}
    text_contents = db.Column(MutableDict.as_mutable(db.PickleType), nullable=True)  # Store text contents as a dictionary {filename: text}

    def set_image_blobs(self, blobs):
        self.image_blobs = blobs

    def get_image_blobs(self):
        return self.image_blobs if self.image_blobs else {}

    def set_text_contents(self, contents):
        self.text_contents = contents

    def get_text_contents(self):
        return self.text_contents if self.text_contents else {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

import os

# Removed /home route to avoid conflict with /index route

@app.route('/', methods=['GET'])
def root():
    return redirect(url_for('index'))

@app.route('/index', methods=['GET', "POST"])
def index():
    image_folder = os.path.join(app.static_folder, 'images', 'home')
    images = []
    if os.path.exists(image_folder):
        for filename in os.listdir(image_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                images.append(filename)

    projects = Project.query.all()

    # Prepare project data with one image and description
    project_data = []
    for project in projects:
        image_filenames = []
        image_blobs = project.get_image_blobs()
        if image_blobs:
            # Get all image filenames
            image_filenames = list(image_blobs.keys())
        project_data.append({
            'id': project.id,
            'name': project.project_name,
            'description': project.description,
            'image_filenames': image_filenames
        })

    return render_template('home.html', images=images, projects=project_data)

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        error = 'Username or password not found'
        return render_template('login.html', login_error=error, username=username)

    session['user_id'] = user.id
    session['username'] = user.username
    session['login_type'] = user.login_type.lower() if user.login_type else None
    flash('Logged in successfully')
    return redirect(url_for('index'))

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username')
    email = request.form.get('email')
    phone = request.form.get('phone')
    dob = request.form.get('dob')
    gender = request.form.get('gender')
    password = request.form.get('password')
    login_type = "broker"
    

    if not username or not phone or not password or not login_type or not dob or not gender or not email:
        flash('Please fill out all fields.')
        return redirect(url_for('login'))

    existing_user = User.query.filter((User.username == username) | (User.phone == phone) | (User.email == email)).first()
    if existing_user:
        flash('User with this username, phone or email already exists.')
        return redirect(url_for('login'))

    from datetime import datetime
    dob_date = datetime.strptime(dob, '%Y-%m-%d').date()

    new_user = User(username=username, email=email, phone=phone, dob=dob_date, gender=gender, login_type=login_type)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    flash('User registered successfully. Please log in.')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/search',methods=['GET',"POST"])
def search():
    return render_template('search.html')

import click

@app.cli.command("recreate-db")
def recreate_db():
    """Recreate the database tables."""
    click.echo("Dropping all tables...")
    db.drop_all()
    click.echo("Creating all tables...")
    db.create_all()
    click.echo("Database recreated successfully.")

import os
from flask import request

@app.route('/broker')
def broker():
    if 'user_id' not in session or session.get('login_type') != 'broker':
        flash('Access denied.')
        return redirect(url_for('login'))
    return render_template('broker.html')

import os

import base64

@app.route('/broker/projects')
def broker_projects():
    if 'user_id' not in session or session.get('login_type') != 'broker':
        flash('Access denied.')
        return redirect(url_for('login'))
    projects = Project.query.all()

    # No longer need to prepare image_data_dict and text_content_dict since template uses Project model data directly
    return render_template('projects.html', projects=projects)

@app.route('/broker/videos')
def broker_videos():
    if 'user_id' not in session or session.get('login_type') != 'broker':
        flash('Access denied.')
        return redirect(url_for('login'))
    # For demonstration, list video files from static/videos folder
    video_folder = os.path.join(app.static_folder, 'videos')
    videos = []
    if os.path.exists(video_folder):
        for filename in os.listdir(video_folder):
            if filename.lower().endswith('.mp4'):
                videos.append({'id': filename, 'filename': filename})
    return render_template('broker_videos.html', videos=videos)

from flask import jsonify

@app.route('/broker/payment', methods=['POST'])
def broker_payment():
    if 'user_id' not in session or session.get('login_type') != 'broker':
        return jsonify({'success': False, 'message': 'Access denied.'}), 403

    video_id = request.form.get('video_id')
    subscription_level = request.form.get('subscription_level')
    card_number = request.form.get('card_number')
    expiry_date = request.form.get('expiry_date')
    cvv = request.form.get('cvv')

    # Basic validation
    if not all([video_id, subscription_level, card_number, expiry_date, cvv]):
        return jsonify({'success': False, 'message': 'Missing payment information.'})

    # Here you would integrate with a real payment gateway API
    # For now, simulate payment success
    payment_success = True

    if payment_success:
        # Provide download URL for the video
        download_url = url_for('static', filename='videos/' + video_id)
        return jsonify({'success': True, 'message': 'Payment successful! Starting download...', 'download_url': download_url})
    else:
        return jsonify({'success': False, 'message': 'Payment failed. Please try again.'})

@app.route('/broker/project/delete/<int:project_id>')
def delete_project(project_id):
    if 'user_id' not in session or session.get('login_type') != 'broker':
        flash('Access denied.')
        return redirect(url_for('login'))
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully.')
    return redirect(url_for('broker_projects'))

@app.route('/broker/project/update_text', methods=['POST'])
def update_project_text():
    # This route is no longer used for single updates
    return redirect(url_for('broker_projects'))

@app.route('/broker/project/update_texts', methods=['POST'])
def update_project_texts():
    user_id = session.get('user_id')
    login_type = session.get('login_type')
    if not user_id or login_type != 'broker':
        flash('Access denied.')
        return redirect(url_for('login'))

    project_id = request.form.get('project_id')
    if not project_id:
        flash('Missing project ID.')
        return redirect(url_for('broker_projects'))

    project = Project.query.get(project_id)
    if not project:
        flash('Project not found.')
        return redirect(url_for('broker_projects'))

    # Update project name
    project_name = request.form.get('project_name')
    if project_name:
        project.project_name = project_name

    # Update project description
    project_description = request.form.get('project_description')
    if project_description is not None:
        project.description = project_description

    # Collect all updated texts and filenames from the form
    updated_texts = {}
    for key in request.form:
        if key.startswith('updated_text_'):
            index = key[len('updated_text_'):]
            text_content = request.form.get(key)
            text_filename_key = f'text_filename_{index}'
            text_filename = request.form.get(text_filename_key)
            if text_filename:
                updated_texts[text_filename] = text_content

    # Save updated texts in the database as text_contents dictionary
    text_contents = project.get_text_contents()
    for filename, content in updated_texts.items():
        text_contents[filename] = content
    project.set_text_contents(text_contents)

    # Handle uploaded images and save as BLOBs
    image_blobs = project.get_image_blobs()
    for key in request.files:
        if key.startswith('updated_image_'):
            file = request.files[key]
            if file and file.filename != '':
                try:
                    file_data = file.read()
                    filename = secure_filename(file.filename)
                    image_blobs[filename] = file_data
                except Exception as e:
                    flash(f'Error processing uploaded image: {e}')
    project.set_image_blobs(image_blobs)

    # Add project to session to ensure change tracking
    db.session.add(project)

    # Save project changes to database
    errors = []
    try:
        db.session.commit()
    except Exception as e:
        errors.append(f'Error saving project updates: {e}')

    if errors:
        flash('Some errors occurred: ' + '; '.join(errors))
    else:
        flash('All texts and images updated successfully.')

    return redirect(url_for('broker_projects'))

@app.route('/broker/upload_images', methods=['POST'])
def broker_upload_images():
    if 'user_id' not in session or session.get('login_type') != 'broker':
        flash('Access denied.')
        return redirect(url_for('login'))

    if 'images' not in request.files:
        return render_template('broker.html', message="No images part in the request.")

    files = request.files.getlist('images')
    if not files or all(file.filename == '' for file in files):
        return render_template('broker.html', message="No selected images.")

    image_blobs = {}
    for file in files:
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            filename = secure_filename(file.filename)
            try:
                file_data = file.read()
                image_blobs[filename] = file_data
            except Exception as e:
                return render_template('broker.html', message=f"Error processing image {filename}: {e}")
        else:
            return render_template('broker.html', message="Invalid file type. Please upload images only.")

    project_name = "Uploaded Images " + str(uuid.uuid4())[:8]
    project = Project(project_name=project_name)
    project.set_image_blobs(image_blobs)
    project.set_text_contents({})  # No text contents initially
    db.session.add(project)
    db.session.commit()

    flash("Images uploaded successfully.")
    return redirect(url_for('broker_projects'))

@app.route('/broker/upload', methods=['POST'])
def broker_upload():
    if 'user_id' not in session or session.get('login_type') != 'broker':
        flash('Access denied.')
        return redirect(url_for('login'))

    if 'pdfFile' not in request.files:
        return render_template('broker.html', message="No file part in the request.")

    file = request.files['pdfFile']
    if file.filename == '':
        return render_template('broker.html', message="No selected file.")

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        from pdftoimages import extract_images_from_pdf
        output_folder = 'static/extracted_images'
        try:
            extract_images_from_pdf(upload_path, output_folder)

            # Save project info in database with image blobs and text contents
            project_name = filename
            image_blobs = {}
            text_contents = {}

            for f in os.listdir(output_folder):
                file_path = os.path.join(output_folder, f)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    with open(file_path, "rb") as img_file:
                        image_blobs[f] = img_file.read()
                elif f.lower().endswith('.txt'):
                    with open(file_path, "r", encoding="utf-8") as txt_file:
                        text_contents[f] = txt_file.read()

            project = Project(project_name=project_name)
            project.set_image_blobs(image_blobs)
            project.set_text_contents(text_contents)
            db.session.add(project)
            db.session.commit()

            message = f"PDF processed successfully. Images and text saved in database."
        except Exception as e:
            message = f"Error processing PDF: {e}"

        return render_template('broker.html', message=message)
    else:
        return render_template('broker.html', message="Invalid file type. Please upload a PDF.")



from flask import send_from_directory, make_response


@app.route('/text_files/<path:filename>')
def serve_text_file(filename):
    # Serve text files with CORS headers to avoid CORB
    response = make_response(send_from_directory('static/extracted_images', filename))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    return response


@app.route('/project_image/<int:project_id>/<filename>')
def project_image(project_id, filename):
    project = Project.query.get_or_404(project_id)
    image_blobs = project.get_image_blobs()
    if filename not in image_blobs:
        return "Image not found", 404
    image_data = image_blobs[filename]
    from flask import Response
    return Response(image_data, mimetype='image/jpeg')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

video_creation_status = {}

def video_creation_task(project_id, option, input_folder, output_folder):
    global video_creation_status
    video_creation_status[project_id] = 'in_progress'
    try:
        if option == 'ai':
            create_video(input_folder=input_folder, output_folder=output_folder)
        elif option == 'user':
            create_video_from_user_text(input_folder=input_folder, output_folder=output_folder)
        else:
            video_creation_status[project_id] = 'error: invalid option'
            return
        video_creation_status[project_id] = 'completed'
    except Exception as e:
        video_creation_status[project_id] = f'error: {str(e)}'

@app.route('/broker/project/create_video/<int:project_id>', methods=['POST'])
def create_video_route(project_id):
    if 'user_id' not in session or session.get('login_type') != 'broker':
        # Return JSON error instead of redirect
        return jsonify({'success': False, 'message': 'Access denied.'}), 403

    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'message': 'Project not found.'}), 404

    # Ensure request content type is JSON
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format, JSON expected.'}), 400

    option = request.json.get('option', 'ai')

    input_folder = os.path.join('static', 'extracted_images')
    output_folder = os.path.join('web_output', str(project_id))
    os.makedirs(output_folder, exist_ok=True)

    # Start background thread for video creation
    thread = threading.Thread(target=video_creation_task, args=(project_id, option, input_folder, output_folder))
    thread.start()

    return jsonify({'success': True, 'message': 'Video creation started.'})

@app.route('/broker/project/create_video_status/<int:project_id>')
def create_video_status(project_id):
    status = video_creation_status.get(project_id, 'not_started')
    return jsonify({'status': status})

