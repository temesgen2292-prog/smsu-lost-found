from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# --- Database setup (SQLite) ---
DB_URL = "sqlite:///lost_found.db"
engine = create_engine(DB_URL, echo=False, future=True)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(120), nullable=False)
    category = Column(String(20), nullable=False)  # "lost" or "found"
    description = Column(Text, nullable=False)
    contact = Column(String(120), nullable=False)
    location = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- Routes ---
@app.route("/")
def home():
    # Renders the front-end from /templates/index.html
    return render_template("index.html")

@app.route("/api/items", methods=["GET"])
def get_items():
    session = SessionLocal()
    try:
        q = session.query(Item).order_by(Item.created_at.desc()).all()
        data = [
            {
                "id": i.id,
                "title": i.title,
                "category": i.category,
                "description": i.description,
                "contact": i.contact,
                "location": i.location,
                "created_at": i.created_at.isoformat()
            }
            for i in q
        ]
        return jsonify(data), 200
    finally:
        session.close()

@app.route("/api/items", methods=["POST"])
def add_item():
    payload = request.get_json(force=True)
    required = ["title", "category", "description", "contact"]
    if any(k not in payload or not str(payload[k]).strip() for k in required):
        return jsonify({"error": "Missing required fields."}), 400

    if payload["category"].lower() not in ["lost", "found"]:
        return jsonify({"error": "Category must be 'lost' or 'found'."}), 400

    session = SessionLocal()
    try:
        item = Item(
            title=payload["title"].strip(),
            category=payload["category"].lower().strip(),
            description=payload["description"].strip(),
            contact=payload["contact"].strip(),
            location=payload.get("location", "").strip()
        )
        session.add(item)
        session.commit()
        return jsonify({"message": "Item added", "id": item.id}), 201
    finally:
        session.close()

@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    session = SessionLocal()
    try:
        item = session.get(Item, item_id)
        if not item:
            return jsonify({"error": "Item not found"}), 404
        session.delete(item)
        session.commit()
        return jsonify({"message": "Deleted"}), 200
    finally:
        session.close()

if __name__ == "__main__":
    # Run: python app.py
    app.run(debug=True)
