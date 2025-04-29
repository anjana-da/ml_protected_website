from flask import Flask, render_template, request, redirect, url_for, flash, session
from joblib import load
import nltk
import re
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import sqlite3
import os

nltk.download('stopwords')
nltk.download('wordnet')

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database file path
DATABASE = 'users.db'

# Load the saved model, vectorizer, and label encoder
model = load("models/best_model.pkl")
vectorizer = load("models/vectorizer.pkl")
label_encoder = load("models/label_encoder.pkl")

# Preprocessing function for user input
def preprocess_text(text):
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()

    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    text = ' '.join(
        lemmatizer.lemmatize(word)
        for word in text.split()
        if word not in stop_words
    )
    return text

# OTP storage (Temporary for session management)
user_otp = {}

# Function to send OTP
def send_otp(email, otp):
    sender_email = "your_email@example.com"
    password = "your_email_password_here"  # Replace with your email's app-specific password
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = email
    message['Subject'] = "Your OTP for Login"
    message.attach(MIMEText(f"Your OTP is: {otp}", 'plain'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, email, message.as_string())
    except Exception as e:
        print(f"Error sending OTP: {e}")

# Function to initialize the database
def init_db():
    print("Initializing database...")
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                mobile TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                employee_id TEXT UNIQUE NOT NULL,
                occupation TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        print("Database initialized successfully.")
    else:
        print("Database already exists.")

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/community')
def community():
    if 'user' in session:
        return render_template('community.html')
    else:
        flash('You must be logged in to access the community page.', 'danger')
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Validate user credentials
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            otp = random.randint(100000, 999999)
            send_otp(email, otp)
            user_otp[email] = otp
            flash("OTP sent to your email", 'info')
            return redirect(url_for('verify_otp', email=email))
        else:
            flash("Invalid credentials", 'danger')
    return render_template('login.html')

@app.route('/verify-otp/<email>', methods=['GET', 'POST'])
def verify_otp(email):
    if request.method == 'POST':
        entered_otp = int(request.form['otp'])
        if email in user_otp and user_otp[email] == entered_otp:
            session['user'] = email
            flash("Login successful", 'success')
            return redirect(url_for('community'))
        else:
            flash("Invalid OTP", 'danger')
    return render_template('verify_otp.html', email=email)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match", 'danger')
            return redirect(url_for('signup'))

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ? OR mobile = ?", (username, email, mobile))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Username, email, or mobile already registered", 'warning')
            conn.close()
            return redirect(url_for('signup'))

        cursor.execute("INSERT INTO users (username, email, mobile, password) VALUES (?, ?, ?, ?)", (username, email, mobile, password))
        conn.commit()
        conn.close()

        flash("Signup successful!", 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        flash("You must be logged in as an admin", 'danger')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        user_message = request.form['message']
        clean_message = preprocess_text(user_message)
        vectorized_message = vectorizer.transform([clean_message]).toarray()
        prediction = model.predict(vectorized_message)[0]
        vulnerability_type = label_encoder.inverse_transform([prediction])[0]
        return render_template('admin.html', result=f"Detected Vulnerability Type: {vulnerability_type}")
    
    return render_template('admin.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE email = ? AND password = ?", (email, password))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session['admin'] = email
            flash("Admin Login successful", 'success')
            return redirect(url_for('admin'))
        else:
            flash("Invalid admin credentials", 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        employee_id = request.form['employee_id']
        occupation = request.form['occupation']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM admins WHERE email = ? OR employee_id = ?", (email, employee_id))
        existing_admin = cursor.fetchone()

        if existing_admin:
            flash("Email or Employee ID already exists", 'warning')
            conn.close()
            return redirect(url_for('admin_signup'))

        cursor.execute("INSERT INTO admins (email, password, employee_id, occupation) VALUES (?, ?, ?, ?)", (email, password, employee_id, occupation))
        conn.commit()
        conn.close()

        flash("Admin account created successfully", 'success')
        return redirect(url_for('admin_login'))

    return render_template('admin_signup.html')

if __name__ == '__main__':
    init_db()  # Initialize database if not already done
    app.run(debug=True)
