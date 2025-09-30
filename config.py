import os
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    # School branding (tweak in base.html/CSS)
    SCHOOL_NAME = "Your School"
    SCHOOL_COLORS = {"primary": "#004080", "accent": "#FFD200"}
