import os, re, secrets
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, redirect, url_for, flash, request, abort,
    send_from_directory, current_app
)
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, scoped_session, joinedload
from config import Config
from models import Base, User, Roles, Category, Item, ItemStatus, Claim, ClaimStatus, Notification
from forms import LoginForm, RegisterForm, ReportItemForm, SearchForm

# ----- App & DB setup -----
app = Flask(__name__, instance_relative_config=True)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.instance_path, exist_ok=True)

# Enable CSRF globally (so failures are surfaced cleanly)
CSRFProtect(app)

engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], future=True)
Session = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))
Base.metadata.create_all(engine)

# ----- Auth -----
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

def unread_count():
    if current_user.is_authenticated:
        with Session() as s:
            return s.query(Notification).filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
    return 0

app.jinja_env.globals.update(unread_count=unread_count)

@login_manager.user_loader
def load_user(user_id):
    with Session() as s:
        return s.get(User, int(user_id))

# ----- Helpers -----
def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return "." in filename and ext in current_app.config["ALLOWED_EXTENSIONS"]

def save_photo(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    fname = secure_filename(file_storage.filename)
    token = secrets.token_hex(6)
    fname = f"{token}_{fname}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
    file_storage.save(path)
    return fname

def admin_required():
    if not current_user.is_authenticated or current_user.role != Roles.ADMIN:
        abort(403)

def notify(user_id, title, body):
    with Session() as s:
        s.add(Notification(user_id=user_id, title=title, body=body))
        s.commit()

# ----- Seed categories (first run) -----
with Session() as s:
    if not s.execute(select(Category)).first():
        for name, slug in [
            ("Electronics", "electronics"), ("Clothing", "clothing"),
            ("Books", "books"), ("Accessories", "accessories"), ("Other", "other")
        ]:
            s.add(Category(name=name, slug=slug))
        s.commit()

# ----- Public pages -----
@app.route("/")
def index():
    with Session() as s:
        total_items = s.scalar(select(func.count(Item.id))) or 0
        returned = s.scalar(select(func.count()).where(Item.status == ItemStatus.RETURNED)) or 0
        claimed  = s.scalar(select(func.count()).where(Item.status == ItemStatus.CLAIMED)) or 0

        recent = (
            s.execute(
                select(Item)
                .options(joinedload(Item.category))   # <-- eager-load category
                .order_by(Item.created_at.desc())
                .limit(8)
            )
            .scalars()
            .all()
        )

        cats = s.execute(select(Category).order_by(Category.name)).scalars().all()

    return render_template("index.html",
                           recent=recent,
                           stats=dict(total=total_items, returned=returned, claimed=claimed),
                           cats=cats)

@app.route("/browse")
@login_required
def browse():
    form = SearchForm(request.args, meta={"csrf": False})
    with Session() as s:
        cats = s.execute(select(Category).order_by(Category.name)).scalars().all()
        form.category.choices = [(-1, "All Categories")] + [(c.id, c.name) for c in cats]

        # start query WITH eager-load
        q = s.query(Item).options(joinedload(Item.category))  # <-- key line

        # filters
        if form.q.data:
            like = f"%{form.q.data.strip()}%"
            q = q.filter(
                Item.name.ilike(like) | Item.description.ilike(like) | Item.location_found.ilike(like)
            )
        if form.category.data and form.category.data != -1:
            q = q.filter(Item.category_id == form.category.data)

        # sort
        if form.sort.data == "date_asc":
            q = q.order_by(Item.date_found.asc())
        elif form.sort.data == "category":
            # joining is fine; joinedload still prevents detached access later
            q = q.join(Category).order_by(Category.name.asc(), Item.date_found.desc())
        else:
            q = q.order_by(Item.date_found.desc())

        items = q.all()
        cats_map = {c.id: c for c in cats}

    return render_template("browse.html", form=form, items=items, cats_map=cats_map)


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    with Session() as s:
        item = s.execute(
            select(Item)
            .options(joinedload(Item.category))      # <-- eager-load category
            .where(Item.id == item_id)
        ).scalar_one_or_none()
        if not item:
            abort(404)
    return render_template("item_detail.html", item=item)


# ----- Auth -----
@app.route("/login", methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with Session() as s:
            user = s.execute(select(User).where(User.email == form.email.data.lower().strip())).scalar_one_or_none()
            if not user or not check_password_hash(user.password_hash, form.password.data):
                flash("Invalid email or password.", "danger")
            elif not user.is_active:
                flash("This account is disabled. Contact an administrator.", "warning")
            else:
                login_user(user, remember=True)
                flash("Welcome back!", "success")
                return redirect(request.args.get("next") or url_for("dashboard"))
    # If POST but invalid, show field errors via template
    return render_template("login.html", form=form)

@app.route("/register", methods=["GET","POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        with Session() as s:
            existing = s.execute(
                select(User).where(User.email == form.email.data.lower().strip())
            ).scalar_one_or_none()
            if existing:
                flash("That email is already registered. Try signing in.", "warning")
            else:
                u = User(
                    name=form.name.data.strip(),
                    email=form.email.data.lower().strip(),
                    password_hash=generate_password_hash(form.password.data),
                    role=Roles.USER,
                )
                s.add(u); s.commit()
                flash("Account created. Please sign in.", "success")
                return redirect(url_for("login"))
    # If POST but invalid, template shows per-field messages
    return render_template("register.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("index"))

# ----- User: report, dashboard, claims -----
@app.route("/report", methods=["GET","POST"])
@login_required
def report():
    with Session() as s:
        cats = s.execute(select(Category).order_by(Category.name)).scalars().all()
    form = ReportItemForm()
    form.category.choices = [(c.id, c.name) for c in cats]
    if form.validate_on_submit():
        photo_filename = save_photo(form.photo.data)
        if not photo_filename:
            photo_filename = "" # ensure NOT NULL tables accept it
        with Session() as s:
            item = Item(
                name=form.name.data.strip(),
                description=form.description.data.strip(),
                category_id=form.category.data,
                location_found=form.location_found.data.strip(),
                date_found=datetime.combine(form.date_found.data, datetime.min.time()),
                photo_path=photo_filename,
                reported_by=current_user.id,
                status=ItemStatus.FOUND,
            )
            s.add(item); s.commit()
        flash("Item submitted for catalog.", "success")
        return redirect(url_for("dashboard"))
    return render_template("report.html", form=form)

@app.route("/dashboard")
@login_required
def dashboard():
    with Session() as s:
        my_items = s.execute(select(Item).where(Item.reported_by == current_user.id).order_by(Item.created_at.desc())).scalars().all()
        my_claims = s.execute(select(Claim).where(Claim.claimer_id == current_user.id).order_by(Claim.created_at.desc())).scalars().all()
    return render_template("dashboard.html", my_items=my_items, my_claims=my_claims)

@app.route("/claim/<int:item_id>", methods=["POST"])
@login_required
def claim(item_id):
    msg = (request.form.get("message") or "").strip()[:1000]
    with Session() as s:
        item = s.get(Item, item_id)
        if not item or item.status != ItemStatus.FOUND:
            flash("This item cannot be claimed.", "warning")
            return redirect(url_for("item_detail", item_id=item_id))
        existing = s.execute(select(Claim).where(Claim.item_id==item_id, Claim.claimer_id==current_user.id)).scalar_one_or_none()
        if existing:
            flash("You already claimed this item.", "info")
        else:
            c = Claim(item_id=item_id, claimer_id=current_user.id, message=msg)
            s.add(c); s.commit()
            admin_ids = [u.id for u in s.query(User).filter(User.role==Roles.ADMIN).all()]
            for aid in admin_ids:
                notify(aid, "New Claim Request", f"A claim was submitted for item #{item.id}: {item.name}")
            flash("Claim submitted. You’ll be notified after verification.", "success")
    return redirect(url_for("item_detail", item_id=item_id))

@app.route("/notifications")
@login_required
def notifications():
    with Session() as s:
        notes = s.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()
        for n in notes:
            if not n.is_read:
               n.is_read = True
        s.commit()
    return render_template("notifications.html", notes=notes)

# ----- Admin management (unchanged routes; still role-checked) ---------------
@app.route("/admin")
@login_required
def admin_dashboard():
    admin_required()
    with Session() as s:
        totals = {
            "items": s.scalar(select(func.count(Item.id))) or 0,
            "claims": s.scalar(select(func.count(Claim.id))) or 0,
            "pending_claims": s.scalar(select(func.count(Claim.id)).where(Claim.status==ClaimStatus.PENDING)) or 0,
            "users": s.scalar(select(func.count(User.id))) or 0,
        }
        latest = s.execute(select(Item).order_by(Item.created_at.desc()).limit(5)).scalars().all()
    return render_template("admin_dashboard.html", totals=totals, latest=latest)

@app.route("/admin/items")
@login_required
def manage_items():
    admin_required()
    with Session() as s:
        items = s.query(Item).order_by(Item.created_at.desc()).all()
    return render_template("manage_items.html", items=items)

@app.route("/admin/items/<int:item_id>/status", methods=["POST"])
@login_required
def set_item_status(item_id):
    admin_required()
    new_status = request.form.get("status")
    if new_status not in (ItemStatus.FOUND, ItemStatus.CLAIMED, ItemStatus.RETURNED):
        abort(400)
    with Session() as s:
        item = s.get(Item, item_id)
        if not item: abort(404)
        item.status = new_status
        s.commit()
    flash("Item status updated.", "success")
    return redirect(url_for("manage_items"))

@app.route("/admin/claims")
@login_required
def manage_claims():
    admin_required()
    with Session() as s:
        claims = s.query(Claim).order_by(Claim.created_at.desc()).all()
    return render_template("manage_claims.html", claims=claims)

@app.route("/admin/claims/<int:claim_id>/<action>", methods=["POST"])
@login_required
def handle_claim(claim_id, action):
    admin_required()
    with Session() as s:
        c = s.get(Claim, claim_id)
        if not c: abort(404)
        if action == "approve":
            c.status = ClaimStatus.APPROVED
            c.item.status = ItemStatus.CLAIMED
            notify(c.claimer_id, "Claim Approved", f"Your claim for '{c.item.name}' was approved.")
        elif action == "reject":
            c.status = ClaimStatus.REJECTED
            notify(c.claimer_id, "Claim Rejected", f"Your claim for '{c.item.name}' was rejected.")
        else:
            abort(400)
        s.commit()
    flash("Claim updated.", "success")
    return redirect(url_for("manage_claims"))

@app.route("/admin/users")
@login_required
def manage_users():
    admin_required()
    with Session() as s:
        users = s.query(User).order_by(User.created_at.desc()).all()
    return render_template("manage_users.html", users=users)

@app.route("/admin/categories", methods=["GET","POST"])
@login_required
def manage_categories():
    admin_required()
    with Session() as s:
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            if name:
                slug = re.sub(r"[^a-z0-9\-]+","-", name.lower()).strip("-")
                s.add(Category(name=name, slug=slug)); s.commit()
                flash("Category added.", "success")
        cats = s.query(Category).order_by(Category.name).all()
    return render_template("manage_categories.html", cats=cats)

# ----- Static uploads -----
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)

# ----- Errors -----
@app.errorhandler(403)
def forbidden(e): return render_template("403.html"), 403

@app.errorhandler(CSRFError)
def handle_csrf(err):
    flash("Form expired or invalid. Please try again.", "warning")
    return redirect(request.referrer or url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)

