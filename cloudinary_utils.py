import cloudinary
import cloudinary.uploader

def init_cloudinary(app):
    """
    Initialize Cloudinary with credentials from app config.
    Make sure your app.config has:
    CLOUD_NAME, API_KEY, API_SECRET
    """
    cloudinary.config(
        cloud_name=app.config['CLOUD_NAME'],
        api_key=app.config['API_KEY'],
        api_secret=app.config['API_SECRET'],
        secure=True
    )

def upload_video(file_stream, filename, folder='mini_netflix'):
    """
    Upload a video file to Cloudinary.
    file_stream : file object
    filename    : name of the file
    folder      : folder in Cloudinary to store the video
    """
    result = cloudinary.uploader.upload(
        file_stream,
        resource_type='video',  # important for videos
        folder=folder,
        public_id=None,
        overwrite=False
    )
    return result
