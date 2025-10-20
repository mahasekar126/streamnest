import os
from flask import Flask, request, render_template, redirect, url_for, flash, session
from dotenv import load_dotenv
from models import db, Video, User
from cloudinary_utils import init_cloudinary, upload_video
import cloudinary
from cloudinary.utils import cloudinary_url
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import requests

# ------------------ INIT APP ------------------
load_dotenv()  # loads .env
app = Flask(__name__)

# Use the same secret name you put in .env
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# ------------------ CONFIG ------------------
# Database (use DATABASE_URL in .env)
database_url = os.getenv('DATABASE_URL', 'sqlite:///videos.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cloudinary credentials from .env (matches your provided .env)
app.config['CLOUDINARY_CLOUD_NAME'] = os.getenv('CLOUDINARY_CLOUD_NAME')
app.config['CLOUDINARY_API_KEY'] = os.getenv('CLOUDINARY_API_KEY')
app.config['CLOUDINARY_API_SECRET'] = os.getenv('CLOUDINARY_API_SECRET')

# ------------------ CONFIGURE CLOUDINARY ------------------
# Initialize Cloudinary with app config
init_cloudinary(app)

# ------------------ INIT DB ------------------
db.init_app(app)

# ------------------ LOGIN MANAGER ------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ------------------ OAUTH ------------------
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
)

# ------------------ CREATE TABLES ------------------
# Create tables if missing (runs once on startup)
with app.app_context():
    db.create_all()

# ------------------ ROUTES ------------------

@app.route('/')
@login_required
def index():
    # Search by title or category if q given
    query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip()
    my_videos = request.args.get('my_videos', '').strip()

    base_query = Video.query

    if query:
        base_query = base_query.filter(
            (Video.title.ilike(f'%{query}%')) |
            (Video.category.ilike(f'%{query}%'))
        )

    if category_filter:
        base_query = base_query.filter(Video.category.ilike(f'%{category_filter}%'))

    if my_videos and current_user.is_authenticated:
        base_query = base_query.filter(Video.user_id == current_user.id)

    videos = base_query.order_by(Video.created_at.desc()).all()
    return render_template('index.html', videos=videos)

# ------------------ AUTH ROUTES ------------------

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
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("Logged in successfully!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

@app.route('/google_login')
def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/google_authorize')
def google_authorize():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    email = user_info['email']
    name = user_info.get('name', email)

    # Check if user exists, if not create
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)
        user.set_password('')  # No password for OAuth users
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Logged in with Google successfully!", "success")
    return redirect(url_for('index'))

# ------------------ VIDEO ROUTES ------------------

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'video' not in request.files:
        flash("No video part", "danger")
        return redirect(url_for('index'))

    video_file = request.files['video']
    if video_file.filename == '':
        flash("No selected file", "danger")
        return redirect(url_for('index'))

    category = request.form.get('category', '').strip() or 'Uncategorized'
    description = request.form.get('description', '').strip()

    try:
        # Upload video to Cloudinary via helper (expected to use cloudinary.uploader.upload)
        res = upload_video(video_file, video_file.filename)
    except Exception as e:
        # If upload fails, show friendly error and log to console
        flash(f"Upload failed: {str(e)}", "danger")
        return redirect(url_for('index'))

    # Generate thumbnail (2 seconds into video)
    try:
        thumbnail_url, _ = cloudinary_url(
            res['public_id'],
            resource_type='video',
            format='jpg',
            transformation={'start_offset': 2, 'width': 300, 'height': 200, 'crop': 'fill'}
        )
    except Exception:
        thumbnail_url = None

    # Save video metadata in DB (only cloudinary URL and metadata, no local file)
    new_video = Video(
        title=video_file.filename,
        public_id=res.get('public_id'),
        url=res.get('secure_url'),
        category=category,
        description=description,
        thumbnail_url=thumbnail_url,
        user_id=current_user.id  # Associate with current user
    )
    db.session.add(new_video)
    db.session.commit()

    flash("Video uploaded successfully!", "success")
    return redirect(url_for('index'))

@app.route('/delete/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = db.session.get(Video, video_id)
    if not video:
        flash("Video not found!", "danger")
        return redirect(url_for('index'))
    # Check if current user owns the video
    if video.user_id != current_user.id:
        flash("You can only delete your own videos!", "danger")
        return redirect(url_for('index'))
    # Delete from cloudinary and DB
    try:
        cloudinary.uploader.destroy(video.public_id, resource_type='video')
    except Exception:
        # if Cloudinary delete fails, still attempt DB deletion
        pass
    db.session.delete(video)
    db.session.commit()
    flash("Video deleted successfully!", "success")
    return redirect(url_for('index'))

@app.route('/watch/<int:video_id>')
def watch(video_id):
    video = db.session.get(Video, video_id)
    if not video:
        flash("Video not found!", "danger")
        return redirect(url_for('index'))
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template('watch.html', video=video, videos=videos)

# ------------------ RUN APP ------------------
if __name__ == '__main__':
    # Use debug only when FLASK_ENV=development
    debug_mode = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=debug_mode)
