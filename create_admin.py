# create_admin.py
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from models import Base, User, Roles

DB_URL = "sqlite:///instance/app.db"

engine = create_engine(DB_URL, future=True)
Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

print("Connecting to", DB_URL)
Base.metadata.create_all(engine)

email = "temesgen2292@gmail.com"
password = "1234"  # for local dev only!

with Session() as s:
    existing = s.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        print(f"User {email} already exists. Updating role to ADMIN.")
        existing.role = Roles.ADMIN
        s.commit()
    else:
        admin = User(
            name="Temesgen Admin",
            email=email.lower().strip(),
            password_hash=generate_password_hash(password),
            role=Roles.ADMIN,
        )
        s.add(admin)
        s.commit()
        print("Admin created:", admin.email)

print("Done.")
