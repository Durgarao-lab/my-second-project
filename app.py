from unicodedata import name
from flask import Flask, jsonify, render_template, redirect, url_for, flash, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import random
import requests
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask_mail import Message
from flask_mail import Mail
import random
import os
import email
import time


app = Flask(__name__)
app.secret_key = "my_super_secret_key_123"

# ============ EMAIL CONFIG ============
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "djganhhh@gmail.com"
app.config['MAIL_PASSWORD'] = "jisbubuibbvnyyua"
app.config['MAIL_DEFAULT_SENDER'] = "djganhhh@gmail.com"

otp_store = {}
reset_otp_store = {}

# ============ DATABASE ============
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ============ EXTENSIONS ============ 
mail = Mail(app)
db = SQLAlchemy(app)

# ============ MODELS ============
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    photo = db.Column(db.String(200))
    
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, nullable=False)  
    customer_id = db.Column(db.Integer, nullable=False)
    mechanic_id = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.String(300))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
#=========== HELPER FUNCTION TO CALCULATE MECHANIC RATING ===========
def get_mechanic_rating(mechanic_id):
    reviews = Review.query.filter_by(mechanic_id=mechanic_id).all()
    if reviews:
        avg = sum(r.rating for r in reviews) / len(reviews)
        return round(avg, 1)
    return 0

class Mechanic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    service = db.Column(db.String(100))
    is_online = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    mechanic_id = db.Column(db.Integer, db.ForeignKey("mechanic.id"), nullable=False)

    service = db.Column(db.String(100))
    status = db.Column(db.String(50), default="Pending")
    price = db.Column(db.Integer, default=0)
    date = db.Column(db.String(50))

    # ✅ Relationship (important for mechanic details in bookings page)
    mechanic = db.relationship("Mechanic", backref="bookings")
# ============ INDEX ============
@app.route("/")
def index():
    return render_template("index.html")

# ============ CUSTOMER AUTH ============
from werkzeug.security import generate_password_hash

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]

        # ✅ Check if email already exists
        if Customer.query.filter_by(email=email).first():
            return render_template("signup.html", error="⚠ Email already registered. Please login.")

        # 🔐 Hash password before saving
        hashed_password = generate_password_hash(password)

        c = Customer(name=name, email=email, password=hashed_password)
        db.session.add(c)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("signup.html")

from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        customer = Customer.query.filter_by(email=email).first()

        if customer and check_password_hash(customer.password, password):
            session["cid"] = customer.id   # ✅ THIS WAS MISSING
            flash("Login successful!", "success")
            return redirect(url_for("customer_dashboard",customer_id=customer.id))
        else:
            flash("Invalid email or password", "danger")

    return render_template("login.html")

@app.route("/forget_password")
def forgetpassword():
    return render_template("forget_password.html")

@app.route('/customer/dashboard/<int:customer_id>')
def customer_dashboard(customer_id):
    customer = Customer.query.get(customer_id)
    bookings = Booking.query.filter_by(customer_id=customer_id).all()

    mechanics = Mechanic.query.filter_by(is_online=True).all()

    return render_template("customer_dashboard.html",
                           customer=customer,
                           bookings=bookings,
                           mechanics=mechanics) 
    
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/profile_pics"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/submit_review/<int:booking_id>", methods=["POST"])
def submit_review(booking_id):
    cid = session.get("cid")
    if "cid" not in session:
        return redirect(url_for("login"))

    booking = Booking.query.get_or_404(booking_id)

    # Prevent duplicate review
    existing = Review.query.filter_by(booking_id=booking_id).first()
    if existing:
        return "You already reviewed this booking"

    rating = int(request.form["rating"])
    review_text = request.form.get("review_text")

    review = Review(
        booking_id=booking_id,
        customer_id=session["cid"],
        mechanic_id=booking.mechanic_id,
        rating=rating,
        review_text=review_text
    )

    db.session.add(review)
    db.session.commit()

    return redirect(url_for("customer_dashboard",customer_id=cid))

@app.route("/customer/profile", methods=["GET", "POST"])
def customer_profile():
    cid = session.get("cid")
    if not cid:
        return redirect(url_for("login"))

    customer = Customer.query.get(cid)

    if request.method == "POST":
        customer.name = request.form["name"]
        customer.email = request.form["email"]
        customer.phone = request.form["phone"]

        # 📸 Handle photo upload
        if "photo" in request.files:
            file = request.files["photo"]
            if file and file.filename != "":
                filename = secure_filename(f"cust_{cid}_" + file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                customer.photo = filename  # Save filename in DB

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("customer_dashboard", customer_id=cid))

    return render_template("customer_profile.html", customer=customer)

@app.route("/cancel_booking/<int:booking_id>", methods=["POST"])
def cancel_booking_customer(booking_id):
    cid = session.get("cid")
    if not cid:
        return redirect(url_for("login"))

    booking = Booking.query.get(booking_id)

    if not booking:
        flash("Booking not found!", "danger")
        return redirect(url_for("customer_dashboard", customer_id=cid))

    # Security: only that customer can cancel their booking
    if booking.customer_id != cid:
        flash("Unauthorized!", "danger")
        return redirect(url_for("customer_dashboard", customer_id=cid))

    # Only pending bookings can be cancelled
    if booking.status != "Pending":
        flash("Only pending bookings can be cancelled!", "warning")
        return redirect(url_for("customer_dashboard", customer_id=cid))

    booking.status = "Cancelled"
    db.session.commit()

    flash("Booking cancelled successfully!", "success")
    return redirect(url_for("customer_dashboard", customer_id=cid))

@app.route("/customer_bookings")
def customer_bookings():
    cid = session.get("cid")
    if not cid:
        return redirect(url_for("login"))

    bookings = Booking.query.filter_by(customer_id=cid).all()
    return render_template("customer_bookings.html", bookings=bookings)

@app.route("/clear_booking_history", methods=["POST"])
def clear_booking_history():
    cid = session.get("cid")
    if not cid:
        return redirect(url_for("login"))

    # delete only cancelled/completed bookings (recommended)
    Booking.query.filter(
        Booking.customer_id == cid,
        Booking.status.in_(["Cancelled", "Completed", "Rejected"])
    ).delete(synchronize_session=False)

    db.session.commit()
    flash("Booking history cleared!", "success")
    return redirect(url_for("customer_bookings"))

# ============ PRICE LIST ============
SERVICE_PRICES = {
    "Chain Lubrication": 100,
    "Puncture Fix": 100,
    "Engine Oil Change": 350,
    "Bike Wash": 120,
    "Full Service": 700,
    "Electrical Repair": 400,
    "Breakdown Assistance": 500
}
# ---------------- BOOKING ----------------
from datetime import datetime

from flask import request, redirect, url_for, flash

@app.route("/book", methods=["POST"])
def book():
    if "cid" not in session:
        flash("Please login first!", "danger")
        return redirect(url_for("login"))

    cid = session["cid"]
    mechanic_id = request.form.get("mechanic_id")
    service = request.form.get("service")

    if not mechanic_id or not service:
        flash("Missing booking details!", "danger")
        return redirect(url_for("customer_dashboard"))

    price = SERVICE_PRICES.get(service, 0)

    booking = Booking(
        customer_id=cid,
        mechanic_id=int(mechanic_id),
        service=service,
        price=price,
        status="Pending",
        date=datetime.now()
    )

    db.session.add(booking)
    db.session.commit()

    print("DEBUG: Booking created with ID", booking.id)
    send_notifications(booking.id)

    flash("✅ Booking Successful!", "success")
    return redirect(url_for("customer_bookings"))

@app.route("/book_from_map", methods=["POST"])
def book_from_map():
    cid = session.get("cid")
    if not cid:
        return jsonify({"status": "error", "message": "Please login first!"})

    data = request.get_json()
    service = data.get("service")

    if not service:
        return jsonify({"status": "error", "message": "No service selected!"})

    # ✅ choose mechanic automatically (pick first online mechanic)
    mechanic = Mechanic.query.filter_by(is_online=True).first()
    if not mechanic:
        return jsonify({"status": "error", "message": "No mechanics online!"})

    price = SERVICE_PRICES.get(service, 0)

    booking = Booking(
        customer_id=cid,
        mechanic_id=mechanic.id,
        service=service,
        price=price,
        status="Pending",
        date=datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )

    db.session.add(booking)
    db.session.commit()

    return jsonify({"status": "ok"})

@app.route("/booking")
def booking_page():
    if "cid" not in session:
        return redirect(url_for("login"))

    mechanics = Mechanic.query.all()
    customer = Customer.query.get(session.get("cid"))
    return render_template("booking.html", mechanics=mechanics, customer=customer)

# ============ NOTIFICATION FUNCTIONS ============
def send_notifications(booking_id):
    print("🔔 Notification function started")

    # ✅ Get booking correctly
    booking = Booking.query.get(booking_id)
    if booking is None:
        print("❌ Booking not found")
        return

    # ✅ Get mechanic & customer from booking
    mech = Mechanic.query.get(booking.mechanic_id)
    cust = Customer.query.get(booking.customer_id)

    if cust is None:
        print("❌ Customer not found")
        return

    # ✅ Use booking.status directly
    status = booking.status

    try:
        msg = Message(
            subject=f"Your Booking is {status}",   # ✅ f-string added
            sender=app.config['MAIL_USERNAME'],
            recipients=[cust.email]
        )

        msg.body = f"""
Hello {cust.name},

Your bike service booking has been updated.

Service: {booking.service}
Mechanic: {mech.name if mech else 'Assigned Mechanic'}
Status: {status}

Thank you for using our service!
"""
        mail.send(msg)
        print("✅ CUSTOMER EMAIL SENT SUCCESSFULLY")

    except Exception as e:
        print("❌ CUSTOMER EMAIL FAILED:", e)

    # Optional: print mechanic info
    if mech:
        print(f"📧 Mechanic Email: {mech.email}")
        print(f"📱 Mechanic Phone: {mech.phone}")
        
# ================= MECHANIC EMAIL (NEW BOOKING ALERT) =================
    if not mech:
        print("❌ Mechanic not found")
        return

    try:
        msg2 = Message(
            subject="🚨 New Service Booking Assigned",
            sender=app.config['MAIL_USERNAME'],
            recipients=[mech.email]
        )

        msg2.body = f"""
Hello {mech.name},

A customer has booked your service.

Customer Name : {cust.name}
Customer Phone: {cust.phone if cust.phone else 'Not Provided'}
Customer Email: {cust.email}

Service Requested: {booking.service}
Booking Time: {booking.date}

Login to your mechanic dashboard to accept or reject the job.
"""

        mail.send(msg2)
        print("✅ MECHANIC BOOKING EMAIL SENT")

    except Exception as e:
        print("❌ MECHANIC EMAIL FAILED:", e)        
        
# ============ INVOICE EMAIL FUNCTION ============

def generate_invoice_pdf(booking, cust, mech):
    folder = "invoices"
    if not os.path.exists(folder):
        os.makedirs(folder)

    invoice_id = f"INV{booking.id:05d}"
    filename = f"{folder}/{invoice_id}.pdf"

    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, height - 50, "BIKE SERVICE INVOICE")

    c.setFont("Helvetica", 12)
    y = height - 100

    c.drawString(50, y, f"Invoice ID: {invoice_id}")
    y -= 25
    c.drawString(50, y, f"Date: {booking.date}")
    y -= 40

    c.drawString(50, y, f"Customer Name: {cust.name}")
    y -= 25
    c.drawString(50, y, f"Customer Email: {cust.email}")
    y -= 40

    c.drawString(50, y, f"Mechanic Name: {mech.name if mech else 'Assigned Mechanic'}")
    y -= 25
    c.drawString(50, y, f"Mechanic Phone: {mech.phone if mech else 'N/A'}")
    y -= 40

    c.drawString(50, y, f"Service Provided: {booking.service}")
    y -= 25
    c.drawString(50, y, f"Total Amount: ₹{booking.price}")
    y -= 50

    c.drawString(50, y, "Thank you for choosing our service!")

    c.save()
    return filename, invoice_id        
        
def send_invoice_email(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return
 
    cust = Customer.query.get(booking.customer_id)
    mech = Mechanic.query.get(booking.mechanic_id)

    if not cust:
        return

    # 🔥 Generate PDF
    pdf_path, invoice_id = generate_invoice_pdf(booking, cust, mech)

    try:
        msg = Message(
            subject="🧾 Your Bike Service Invoice",
            sender=app.config['MAIL_USERNAME'],
            recipients=[cust.email]
        )

        msg.body = f"""
Hello {cust.name},

Your bike service is completed successfully 🎉

Invoice ID: {invoice_id}
Service: {booking.service}
Amount Paid: ₹{booking.price}

Please find your invoice attached.

Thank you for choosing us!
"""

        # 📎 Attach PDF
        with open(pdf_path, "rb") as f:
            msg.attach(f"{invoice_id}.pdf", "application/pdf", f.read())

        mail.send(msg)
        print("✅ INVOICE EMAIL WITH PDF SENT")

    except Exception as e:
        print("❌ INVOICE EMAIL FAILED:", e)
 
 # ---------------- SEND SMS ----------------
    try:
        if mech.phone:
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = {
                "sender_id": "TXTIND",
                "message": f"New booking from {cust.name} for service: {booking.service}",
                "language": "english",
                "route": "v3",
                "numbers": mech.phone
            }
            headers = {
                "authorization": "tpI7jDrgvawbVFKoGTBcqeYC4ZziWhu31M5dEnOL9J0mUfR6HAofdTSDh5LJiO2kxaEYcQp0IvgrVBFq",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            r = requests.post(url, data=payload, headers=headers)
            print("📨 SMS RESPONSE:", r.text)
        else:
            print("❌ Mechanic phone number missing")

    except Exception as e:
        print("❌ SMS FAILED:", e)

# ============ MECHANIC AREA ============
@app.route("/signup_mechanic", methods=["GET", "POST"])
def signup_mechanic():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]   # ✅ ADD THIS LINE
        service = request.form.get("service")

        if Mechanic.query.filter_by(email=email).first():
            return "<script>alert('⚠ Email already exists!'); window.location='/signup_mechanic';</script>"

        if Mechanic.query.filter_by(phone=phone).first():
            return "<script>alert('⚠ Phone already registered!'); window.location='/signup_mechanic';</script>"
        
        if Mechanic.query.filter_by(service=service).first():
            return "<script>alert('⚠ Service already registered!'); window.location='/signup_mechanic';</script>"
        
        # 🔐 Hash password (since we enabled hashing)
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(password)
        mech = Mechanic(name=name, email=email, password=hashed_password, phone=phone)
        db.session.add(mech)
        db.session.commit()

        return "<script>alert('Signup Successful! Login now'); window.location='/mechanic_login';</script>"

    return render_template("signup_mechanic.html")

from werkzeug.security import check_password_hash, generate_password_hash

from werkzeug.security import check_password_hash, generate_password_hash

@app.route("/mechanic_login", methods=["GET", "POST"])
def mechanic_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        print("Entered Email:", email)
        print("Entered Password:", password)

        mech = Mechanic.query.filter_by(email=email).first()

        if not mech:
            print("❌ No mechanic found with this email")
            return render_template("mechanic_login.html", error="Invalid Email or Password ❌")

        print("DB Password:", mech.password)

        # ✅ If password is hashed (pbkdf2 or scrypt)
        if mech.password.startswith(("pbkdf2:", "scrypt:")):
            if check_password_hash(mech.password, password):
                session.clear()  # 🔥 clear old sessions
                session["mid"] = mech.id
                print("✅ LOGIN SUCCESS (HASHED)")
                return redirect(url_for("mechanic_dashboard"))
            else:
                print("❌ Hash password check failed")

        # ✅ If old plain password (first login after upgrade)
        elif mech.password == password:
            print("🔄 Upgrading plain password to hashed")
            mech.password = generate_password_hash(password)
            db.session.commit()

            session.clear()
            session["mid"] = mech.id
            print("✅ LOGIN SUCCESS (UPGRADED)")
            return redirect(url_for("mechanic_dashboard"))

        else:
            print("❌ Password does not match")

    return render_template("mechanic_login.html", error="Invalid Email or Password ❌")

# ✅ FIXED FUNCTION (THIS CAUSED YOUR ERROR)
@app.route("/mechanicforgetpassword")
def mechanic_forget_password():
    return render_template("mechanicforgetpassword.html")

@app.route("/mechanic_dashboard")
def mechanic_dashboard():
    if "mid" not in session:
        return redirect(url_for("mechanic_login"))
    
    mech_id = session["mid"]
    mechanic = Mechanic.query.get(mech_id)
    #=========== GET MECHANIC RATING ============
    rating = get_mechanic_rating(mechanic.id)

    return render_template("mechanic_dashboard.html", mechanic=mechanic, rating=rating)

@app.route("/mechanic/accept/<int:bid>/<int:mid>")
def accept_booking(bid, mid):
    b = Booking.query.get_or_404(bid)
    b.status = "Accepted"
    db.session.commit()
# Send notification to customer about acceptance
    send_notifications(b.id)  # Call notification function
    
    return redirect(url_for("mechanic_requests", mech_id=mid))

@app.route("/mechanic/reject/<int:bid>/<int:mid>")
def reject_booking(bid, mid):
    b = Booking.query.get_or_404(bid)
    b.status = "Rejected"
    db.session.commit()
    
    # Send notification to customer about rejection
    send_notifications(b.id)  # Call notification function
    
    return redirect(url_for("mechanic_requests", mech_id=mid))

@app.route("/mechanic/set_status/<int:mid>/<status>")
def set_status(mid, status):
    mech = Mechanic.query.get(mid)
    mech.is_online = (status == "online")
    db.session.commit()
    return "ok"

@app.route("/mechanic/requests/<int:mech_id>")
def mechanic_requests(mech_id):
    mechanic = Mechanic.query.get(mech_id)
    requests = Booking.query.filter_by(mechanic_id=mech_id).all()

    # Build list containing booking + customer name
    req_list = []
    for r in requests:
        customer = Customer.query.get(r.customer_id)
        req_list.append({
            "id": r.id,
            "service": r.service,
            "status": r.status,
            "customer_name": customer.name if customer else "Unknown"
        })

    return render_template("mechanic_requests.html", mechanic=mechanic, requests=req_list)

@app.route("/mechanic/jobs/<int:mid>")
def mechanic_jobs(mid):
    mechanic = Mechanic.query.get(mid)
    jobs = Booking.query.filter_by(mechanic_id=mid).all()
    return render_template("mechanic_jobs.html", mechanic=mechanic, jobs=jobs)

@app.route("/mechanic/job/accept/<int:bid>")
def accept_job_from_jobs(bid):
    mid = session.get("mid")
    if not mid:
        return redirect(url_for("mechanic_login"))

    b = Booking.query.get_or_404(bid)
    b.status = "Accepted"
    db.session.commit()

    return redirect(url_for("mechanic_jobs", mid=mid))

@app.route("/mechanic/job/reject/<int:bid>")
def reject_job_from_jobs(bid):
    mid = session.get("mid")
    if not mid:
        return redirect(url_for("mechanic_login"))

    b = Booking.query.get_or_404(bid)
    b.status = "Rejected"
    db.session.commit()

    return redirect(url_for("mechanic_jobs", mid=mid))

@app.route("/mechanic/job/complete/<int:bid>")
def job_complete(bid):
    job = Booking.query.get(bid)
    job.status = "Completed"
    db.session.commit()
    send_invoice_email(job.id)  # Send invoice email to customer
    return redirect(request.referrer)

@app.route("/mechanic/earnings/<int:mech_id>")
def mechanic_earnings(mech_id):
    mechanic = Mechanic.query.get_or_404(mech_id)
    jobs = Booking.query.filter_by(mechanic_id=mech_id, status="Completed").all()
    total_earnings = sum(job.price for job in jobs)
    return render_template("mechanic_earnings.html", mechanic=mechanic, jobs=jobs, total=total_earnings)

# ---------------- PROFILE ----------------
@app.route("/mechanic/profile/<int:mid>", methods=["GET", "POST"])
def mechanic_profile(mid):
    mech = Mechanic.query.get_or_404(mid)

    if request.method == "POST":
        mech.name = request.form["name"]
        mech.email = request.form["email"]
        mech.phone = request.form["phone"]
        mech.password = request.form["password"]
        db.session.commit()
        return redirect(url_for("mechanic_dashboard", mech_id=mid))

    return render_template("mechanic_profile.html", mechanic=mech)

# ============ ONLINE STATUS UPDATE ============
@app.route("/mechanic/location", methods=["POST"])
def mechanic_location():
    data = request.json
    mech = Mechanic.query.get(data["id"])
    mech.latitude = data["lat"]
    mech.longitude = data["lng"]
    mech.is_online = True
    db.session.commit()
    return jsonify({"status":"online"})

@app.route("/api/mechanics")
def api_mechanics():
    mechanics = Mechanic.query.filter_by(is_online=True).all()
    return jsonify([{"id":m.id,"name":m.name,"phone":m.phone,"lat":m.latitude,"lng":m.longitude} for m in mechanics])


# ============ MAP ============
@app.route("/map")
def map_page():
    return render_template("map.html")

# ============ OTP ============
@app.route("/send-otp", methods=["POST"])
def send_otp():
    email = request.form.get("email")
    if not email:
        return "no_email"

    otp = str(random.randint(100000, 999999))
    otp_store[email] = otp

    try:
        msg = Message("Your OTP Code", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Your OTP is {otp}, It is valid for 5 minutes."
        mail.send(msg)
        return "OTP Sent"
    except:
        return "error"

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    email = request.form.get("email")
    otp = request.form.get("otp")

    print("DEBUG EMAIL:", email, "OTP RECEIVED:", otp)
    print("DEBUG STORED OTP:", otp_store.get(email))

    if otp_store.get(email) and otp_store.get(email).strip() == otp.strip():
        return "OTP verified"

    return "Invalid OTP"

# ================= PASSWORD RESET OTP =================
@app.route("/send-reset-otp", methods=["POST"])
def send_reset_otp():
    email = request.json.get("email")

    if not email:
        return jsonify({"status": "error", "message": "Email required"})

    # Check if email exists (Customer or Mechanic)
    user = Customer.query.filter_by(email=email).first() or Mechanic.query.filter_by(email=email).first()
    if not user:
        return jsonify({"status": "error", "message": "Email not registered"})

    otp = str(random.randint(100000, 999999))
    expiry = time.time() + 300  # 5 minutes

    reset_otp_store[email] = {"otp": otp, "expires": expiry}

    try:
        msg = Message("Password Reset OTP", 
                      sender=app.config['MAIL_DEFAULT_SENDER'],
                      recipients=[email])
        msg.body = f"Your OTP for password reset is {otp}. It is valid for 5 minutes."
        mail.send(msg)
        print("RESET OTP SENT:", email, otp)
        return jsonify({"status": "success"})
    except Exception as e:
        print("MAIL ERROR:", e)
        return jsonify({"status": "error", "message": "Mail failed"})
    
@app.route("/verify-reset-otp", methods=["POST"])
def verify_reset_otp():
    email = request.json.get("email")
    otp = request.json.get("otp")

    data = reset_otp_store.get(email)

    if not data:
        return jsonify({"status": "error", "message": "No OTP requested"})

    if time.time() > data["expires"]:
        return jsonify({"status": "error", "message": "OTP expired"})

    if data["otp"] != otp:
        return jsonify({"status": "error", "message": "Invalid OTP"})

    return jsonify({"status": "verified"})

@app.route("/reset-password", methods=["POST"])
def reset_password():
    email = request.json.get("email")
    new_password = request.json.get("password")

    data = reset_otp_store.get(email)
    if not data:
        return jsonify({"status": "error", "message": "OTP verification required"})

    if time.time() > data["expires"]:
        return jsonify({"status": "error", "message": "OTP expired"})

    user = Customer.query.filter_by(email=email).first() or Mechanic.query.filter_by(email=email).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"})

    user.password = generate_password_hash(new_password)
    db.session.commit()

    reset_otp_store.pop(email, None)

    return jsonify({"status": "success"})

# ============ LOGOUT ============
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ============ RUN ============
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True, port=3000)