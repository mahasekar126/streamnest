import os
from flask import Flask, request, render_template, redirect, url_for, flash
from dotenv import load_dotenv
from models import db, Video, User
from cloudinary_utils import init_cloudinary, upload_video
import cloudinary
from cloudinary.utils import cloudinary_url
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------ INIT APP ------------------
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# ------------------ CONFIG ------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///videos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CLOUD_NAME'] = os.getenv('CLOUDINARY_CLOUD_NAME')
app.config['API_KEY'] = os.getenv('CLOUDINARY_API_KEY')
app.config['API_SECRET'] = os.getenv('CLOUDINARY_API_SECRET')

# ------------------ INIT DB & CLOUDINARY ------------------
db.init_app(app)
init_cloudinary(app)

# ------------------ LOGIN MANAGER ------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ CREATE TABLES ------------------
with app.app_context():
    db.create_all()

# ------------------ ROUTES ------------------

# Home / Library (protected)
@app.route('/')
@login_required
def index():
    query = request.args.get('q', '').strip()
    if query:
        videos = Video.query.filter(
            (Video.title.ilike(f'%{query}%')) |
            (Video.category.ilike(f'%{query}%'))
        ).order_by(Video.created_at.desc()).all()
    else:
        videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template('index.html', videos=videos)

# ------------------ AUTH ROUTES ------------------

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for('register'))

        new_user = User(email=email)
        new_user.password_hash = generate_password_hash(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash("Logged in successfully!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

# ------------------ VIDEO ROUTES ------------------

# Upload Video (protected)
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'video' not in request.files:
        return "No video part", 400

    video_file = request.files['video']
    if video_file.filename == '':
        return "No selected file", 400

    category = request.form.get('category', '').strip() or 'Uncategorized'
    description = request.form.get('description', '').strip()

    # Upload video to Cloudinary
    res = upload_video(video_file, video_file.filename)

    # Generate thumbnail
    thumbnail_url, _ = cloudinary_url(
        res['public_id'],
        resource_type='video',
        format='jpg',
        transformation={'start_offset': 2, 'width': 300, 'height': 200, 'crop': 'fill'}
    )

    # Save video in DB
    new_video = Video(
        title=video_file.filename,
        public_id=res['public_id'],
        url=res['secure_url'],
        category=category,
        description=description,
        thumbnail_url=thumbnail_url
    )
    db.session.add(new_video)
    db.session.commit()

    flash("Video uploaded successfully!", "success")
    return redirect(url_for('index'))

# Delete Video (protected)
@app.route('/delete/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    cloudinary.uploader.destroy(video.public_id, resource_type='video')
    db.session.delete(video)
    db.session.commit()
    flash("Video deleted successfully!", "success")
    return redirect(url_for('index'))

# Watch Video (protected)
@app.route('/watch/<int:video_id>')
@login_required
def watch(video_id):
    video = Video.query.get_or_404(video_id)
    return render_template('watch.html', video=video)

# ------------------ RUN APP ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
