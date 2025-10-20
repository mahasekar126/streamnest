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
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    public_id = f"uploads/{filename.split('.')[0]}_{unique_id}"
    return cloudinary.uploader.upload(
        file,
        resource_type='video',
        public_id=public_id,
        overwrite=True
    )
