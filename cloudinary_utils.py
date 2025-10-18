import cloudinary
import cloudinary.uploader

def init_cloudinary(app):
    cloudinary.config(
        cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
        api_key=app.config.get('CLOUDINARY_API_KEY'),
        api_secret=app.config.get('CLOUDINARY_API_SECRET'),
        secure=True
    )

def upload_video(file, filename):
    return cloudinary.uploader.upload(
        file,
        resource_type='video',
        folder='uploads',
        public_id=filename.split('.')[0],
        overwrite=True
    )
