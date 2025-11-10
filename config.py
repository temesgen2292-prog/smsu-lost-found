import os

class Config:
    # SECURITY
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    WTF_CSRF_ENABLED = True

    # DATABASE
    SQLALCHEMY_DATABASE_URI = "sqlite:///instance/app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # FILE UPLOADS
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

    # BRANDING
    SCHOOL_NAME = "Southwest Minnesota State University"
    SCHOOL_COLORS = {
        "primary": "#4B2E83",   # SMSU Purple
        "accent":  "#B3A369"    # SMSU Gold
    }

    # EMAIL RULES (registration)
    ALLOWED_EMAIL_DOMAINS = {"go.minnstate.edu", "minnstate.edu"}
