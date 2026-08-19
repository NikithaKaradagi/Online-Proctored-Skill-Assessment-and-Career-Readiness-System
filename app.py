from PIL import Image
from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------------- DATABASE CONFIG ----------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Nikitha@566'
app.config['MYSQL_DB'] = 'opsacrs'

# ---------------- UPLOAD FOLDER CONFIG ----------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        fullname = request.form['fullname']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        dob = request.form['dob']
        course = request.form['course']
        college = request.form['college']

        photo = request.files.get('photo')
        filename = None   # Important

        if photo and photo.filename != "":
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cur = mysql.connection.cursor()

        # Check duplicate email
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            cur.close()
            return render_template('register.html', error="Account already exists")

        # Insert user
        cur.execute("""
            INSERT INTO users (fullname, email, password, dob, course, college, photo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (fullname, email, password, dob, course, college, filename))

        mysql.connection.commit()
        cur.close()

        return redirect('/')

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[3], password):

            session['user_id'] = user[0]
            session['fullname'] = user[1]
            session['photo'] = user[7]   # adjust index if needed

            return redirect('/home')   # ✅ NOT url_for wrong name

        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html',)


#----------------Email Function SMTP------------------
import smtplib
from email.mime.text import MIMEText

def send_otp(email, otp):

    sender = "nikithakaradadagi@gmail.com"
    app_password = "awvrmytyxttbebvi"  # your app password (no spaces)

    subject = "OTP - Career Readiness System"

    body = f"""
    Your OTP is: {otp}
    Do not share this code.
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, app_password)
        server.sendmail(sender, email, msg.as_string())
        server.quit()

        print("✅ OTP sent to email")

    except Exception as e:
        print("❌ Error:", e)
#----------------OTP-----------
import random
from werkzeug.security import generate_password_hash

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == 'POST':

        # STEP 1 → CHECK EMAIL
        if 'email' in request.form:
            email = request.form['email']

            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()

            # ❌ EMAIL NOT FOUND
            if not user:
                return render_template(
                    'forgot_password.html',
                    step="email",
                    error="Email not registered. Please create an account."
                )

            # ✅ EMAIL EXISTS → SEND OTP
            otp = str(random.randint(100000, 999999))

            session['reset_email'] = email
            session['reset_otp'] = otp

            send_otp(email, otp)

            return render_template('forgot_password.html', step="otp")

        # STEP 2 → VERIFY OTP
        elif 'otp' in request.form:
            entered_otp = request.form['otp']

            if entered_otp == session.get('reset_otp'):
                return render_template('forgot_password.html', step="reset")
            else:
                return render_template(
                    'forgot_password.html',
                    step="otp",
                    error="Invalid OTP"
                )

        # STEP 3 → RESET PASSWORD
        elif 'password' in request.form:
            new_password = generate_password_hash(request.form['password'])
            email = session.get('reset_email')

            cur = mysql.connection.cursor()
            cur.execute(
                "UPDATE users SET password=%s WHERE email=%s",
                (new_password, email)
            )
            mysql.connection.commit()
            cur.close()

            session.pop('reset_otp', None)
            session.pop('reset_email', None)

            return redirect('/')

    return render_template('forgot_password.html', step="email")
# ---------------- HOME ----------------
@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('home.html', name=session['fullname'])

@app.route('/exam_instructions')
def exam_instructions():
    if 'user_id' not in session:
        return redirect('/')
    return render_template("exam_instructions.html")


from flask import render_template, request, redirect, session
import subprocess

# =========================
# MAIN EXAM ENTRY
# =========================
@app.route('/exam')
def exam():
    # reset result save flag for new attempt
    session.pop("result_saved", None)

    # also reset answers (optional but recommended)
    session.pop("answers", None)
    session.pop("answers_pseudo", None)
    session.pop("status", None)
    session.pop("status_pseudo", None)

    return redirect('/exam/aptitude/1')


# =========================
# APTITUDE SECTION
# =========================
import random

@app.route('/exam/aptitude/<int:qno>', methods=['GET', 'POST'])
def aptitude(qno):

    cur = mysql.connection.cursor()

    # 🔥 RANDOM LOGIC HERE
    if 'aptitude_questions' not in session:
        cur.execute("SELECT * FROM aptitude_questions")
        all_questions = cur.fetchall()
        session['aptitude_questions'] = random.sample(all_questions, 20)

    questions = session['aptitude_questions']
    total = len(questions)

    # -------- YOUR EXISTING CODE --------
    if 'status' not in session:
        session['status'] = {}
    if 'answers' not in session:
        session['answers'] = {}

    status = session['status']
    answers = session['answers']

    if str(qno) not in status:
        status[str(qno)] = "visited"

    if request.method == 'POST':

        selected = request.form.get('answer')

        if selected:
            status[str(qno)] = "answered"
            answers[str(qno)] = selected
        else:
            status[str(qno)] = "visited"

        session['status'] = status
        session['answers'] = answers

        if qno < total:
            return redirect(f'/exam/aptitude/{qno + 1}')
        else:
            session['aptitude_done'] = True
            return redirect('/exam/pseudocode/1')

    question = questions[qno - 1]

    return render_template(
        "exam.html",
        question=question,
        qno=qno,
        total=total,
        base_url="/exam/aptitude",
        section="aptitude",
        status=status,
        answers=answers
    )
    return redirect("/exam/pseudocode/1")
# =========================
# PSEUDOCODE SECTION
# =========================
import random

@app.route('/exam/pseudocode/<int:qno>', methods=['GET', 'POST'])
def pseudocode(qno):

    cur = mysql.connection.cursor()

    # 🔥 RANDOM LOGIC
    if 'pseudo_questions' not in session:
        cur.execute("SELECT * FROM pseudocode_questions")
        all_questions = cur.fetchall()

        session['pseudo_questions'] = random.sample(all_questions, 10)

    questions = session['pseudo_questions']
    total = len(questions)

    # -------- EXISTING CODE --------
    if 'status_pseudo' not in session:
        session['status_pseudo'] = {}
    if 'answers_pseudo' not in session:
        session['answers_pseudo'] = {}

    status = session['status_pseudo']
    answers = session['answers_pseudo']

    if str(qno) not in status:
        status[str(qno)] = "visited"

    if request.method == 'POST':
        selected = request.form.get('answer')

        if selected:
            status[str(qno)] = "answered"
            answers[str(qno)] = selected
        else:
            status[str(qno)] = "visited"

        session['status_pseudo'] = status
        session['answers_pseudo'] = answers

        if qno < total:
            return redirect(f'/exam/pseudocode/{qno + 1}')
        else:
            session['pseudocode_done'] = True
            return redirect('/exam/coding/1')

    question = questions[qno - 1]

    return render_template(
        "exam.html",
        question=question,
        qno=qno,
        total=total,
        base_url="/exam/pseudocode",
        section="pseudo",
        status=status,
        answers=answers
    )

    return redirect("/exam/coding/1")

# =========================
# CODING SECTION
# =========================
import random

@app.route('/exam/coding/<int:qno>')
def coding(qno):

    cur = mysql.connection.cursor()

    # 🔥 RANDOM LOGIC
    if 'coding_question' not in session:
        cur.execute("SELECT * FROM coding_questions")
        all_questions = cur.fetchall()

        session['coding_question'] = random.choice(all_questions)

    question = session['coding_question']
    total = 1

    return render_template(
        "exam.html",
        question=question,
        qno=1,  # always 1
        total=1,
        base_url="/exam/coding",
        section="coding",
        status={}
    )
# =========================
# =========================
# RUN CODE
# =========================
import subprocess
from flask import request, jsonify, session

@app.route('/run_code', methods=['POST'])
def run_code():

    code = request.form.get('code')
    lang = request.form.get('language')

    try:

        # ---------- PYTHON ----------
        if lang == "python":

            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )

        # ---------- C ----------
        elif lang == "c":

            with open("temp.c", "w") as f:
                f.write(code)

            subprocess.run(
                ["gcc", "temp.c", "-o", "temp"],
                check=True
            )

            result = subprocess.run(
                ["temp.exe"],
                capture_output=True,
                text=True
            )

        # ---------- C++ ----------
        elif lang == "cpp":

            with open("temp.cpp", "w") as f:
                f.write(code)

            subprocess.run(
                ["g++", "temp.cpp", "-o", "temp"],
                check=True
            )

            result = subprocess.run(
                ["temp.exe"],
                capture_output=True,
                text=True
            )

        # ---------- JAVA ----------
        elif lang == "java":

            with open("Main.java", "w") as f:
                f.write(code)

            subprocess.run(
                ["javac", "Main.java"],
                check=True
            )

            result = subprocess.run(
                ["java", "Main"],
                capture_output=True,
                text=True
            )

        # ---------- R ----------
        elif lang == "r":

            with open("temp.R", "w") as f:
                f.write(code)

            result = subprocess.run(
                ["Rscript", "temp.R"],
                capture_output=True,
                text=True
            )

        else:
            return jsonify({
                "error": "Language not supported"
            })

        # =========================
        # USER OUTPUT
        # =========================
        output = result.stdout.strip()

        # =========================
        # CODING SCORE
        # =========================
        coding_score = 0

        question = session.get('coding_question')

        if question:

            # correct_answer = LAST COLUMN
            correct_answer = str(question[-1]).strip()

            if output.lower() == correct_answer.lower():
                coding_score = 1

        session['coding_score'] = coding_score

        # =========================
        # RETURN RESULT
        # =========================
        return jsonify({
            "output": result.stdout,
            "error": result.stderr,
            "coding_score": coding_score
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        })
# ---------------- SUBMIT EXAM ----------------
@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    if 'user_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # Get only the questions shown in this exam
    question_ids = session.get('exam_questions', [])

    if not question_ids:
        return redirect('/home')

    format_strings = ','.join(['%s'] * len(question_ids))

    cur.execute(f"""
        SELECT id, correct_option, topic
        FROM questions
        WHERE id IN ({format_strings})
    """, tuple(question_ids))

    questions = cur.fetchall()

    total_score = 0
    topic_scores = {}

    for q in questions:
        q_id = q[0]
        correct_option = str(q[1])
        topic = q[2]

        selected_option = request.form.get(f'q{q_id}')

        if topic not in topic_scores:
            topic_scores[topic] = 0

        if selected_option == correct_option:
            total_score += 1
            topic_scores[topic] += 1

    # Store attempt in database
    cur.execute("""
        INSERT INTO exam_attempts (user_id, score, total_questions)
        VALUES (%s, %s, %s)
    """, (session['user_id'], total_score, len(question_ids)))

    mysql.connection.commit()
    cur.close()

    # Store result temporarily for result page
    session['topic_scores'] = topic_scores
    session['total_score'] = total_score

    return redirect('/result')


# ---------------- RESULT ----------------
# =========================

# RESULT

# =========================

@app.route('/result')

def result():

    if 'user_id' not in session:

        return redirect('/')

    # =========================

    # GET QUESTIONS

    # =========================

    aptitude_q = session.get('aptitude_questions', [])

    pseudo_q = session.get('pseudo_questions', [])

    aptitude_ans = session.get('answers', {})

    pseudo_ans = session.get('answers_pseudo', {})

    # =========================

    # APTITUDE SCORE

    # =========================

    apt_score = 0

    for i, q in enumerate(aptitude_q, start=1):

        if str(i) in aptitude_ans:

            if aptitude_ans[str(i)] == q[6]:

                apt_score += 1

    # =========================

    # PSEUDOCODE SCORE

    # =========================

    pseudo_score = 0

    for i, q in enumerate(pseudo_q, start=1):

        if str(i) in pseudo_ans:

            if pseudo_ans[str(i)] == q[6]:

                pseudo_score += 1

    # =========================

    # CODING SCORE

    # =========================

    coding_score = session.get('coding_score', 0)

    # =========================

    # TOTALS

    # =========================

    apt_total = len(aptitude_q)

    pseudo_total = len(pseudo_q)

    coding_total = 1

    total = apt_total + pseudo_total + coding_total

    score = apt_score + pseudo_score + coding_score

    # =========================

    # PERCENTAGE

    # =========================

    if total > 0:

        percentage = round((score / total) * 100, 2)

    else:

        percentage = 0

    # =========================

    # SAVE HISTORY

    # =========================

    if not session.get("result_saved"):

        cur = mysql.connection.cursor()

        cur.execute("""

            INSERT INTO exam_attempts

            (user_id, score, total_questions)

            VALUES (%s, %s, %s)

        """, (

            session['user_id'],

            score,

            total

        ))

        mysql.connection.commit()

        cur.close()

        session["result_saved"] = True

    # =========================

    # RESULT PAGE

    # =========================

    return render_template(

        "result.html",

        apt_score=apt_score,

        apt_total=apt_total,

        pseudo_score=pseudo_score,

        pseudo_total=pseudo_total,

        coding_score=coding_score,

        coding_total=coding_total,

        score=score,

        total=total,

        percentage=percentage

    )
# ---------------- PROFILE ----------------

from PIL import Image, ExifTags
import os

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        fullname = request.form['fullname']
        dob = request.form['dob']
        course = request.form['course']
        college = request.form['college']

        # Update basic details
        cur.execute("""
            UPDATE users
            SET fullname=%s, dob=%s, course=%s, college=%s
            WHERE id=%s
        """, (fullname, dob, course, college, session['user_id']))

        # ===== Handle profile photo upload =====
        photo = request.files.get('photo')

        if photo and photo.filename != "":
            image = Image.open(photo)

            # -------- FIX ROTATION (EXIF) --------
            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break

                exif = image._getexif()

                if exif is not None:
                    orientation_value = exif.get(orientation)

                    if orientation_value == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation_value == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation_value == 8:
                        image = image.rotate(90, expand=True)

            except:
                pass
            # -------------------------------------

            image = image.convert("RGB")

            # -------- TOP-FOCUSED CROP (FACE SAFE) --------
            width, height = image.size
            min_dim = min(width, height)

            left = (width - min_dim) // 2
            top = 0                     # Crop from TOP
            right = left + min_dim
            bottom = min_dim

            image = image.crop((left, top, right, bottom))
            image = image.resize((300, 300))
            # ---------------------------------------------

            filename = f"profile_{session['user_id']}.png"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            image.save(save_path)

            cur.execute(
                "UPDATE users SET photo=%s WHERE id=%s",
                (filename, session['user_id'])
            )

            session['photo'] = filename

        mysql.connection.commit()

        session['fullname'] = fullname

    # Fetch updated user data
    cur.execute("""
        SELECT fullname, email, dob, course, college, photo
        FROM users
        WHERE id=%s
    """, (session['user_id'],))

    user = cur.fetchone()
    cur.close()

    return render_template('profile.html', user=user)

# ---------------- RESUME ----------------
@app.route('/resume', methods=['GET','POST'])
def resume():
    if 'user_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # Upload
    if request.method == 'POST':
        file = request.files.get('resume')

        if file and file.filename != "":
            filename = secure_filename(file.filename)

            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            cur.execute(
                "INSERT INTO resumes(user_id,file_name) VALUES(%s,%s)",
                (session['user_id'], filename)
            )
            mysql.connection.commit()

    # Fetch resumes
    cur.execute(
        "SELECT id, file_name, uploaded_at FROM resumes WHERE user_id=%s",
        (session['user_id'],)
    )
    resumes = cur.fetchall()
    cur.close()

    return render_template('resume.html', resumes=resumes)


# ---------------- VIEW FILE ROUTE ----------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ---------------- DELETE RESUME ----------------
@app.route('/delete_resume/<int:resume_id>')
def delete_resume(resume_id):
    if 'user_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT file_name FROM resumes WHERE id=%s AND user_id=%s",
        (resume_id, session['user_id'])
    )
    result = cur.fetchone()

    if result:
        filename = result[0]
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        if os.path.exists(file_path):
            os.remove(file_path)

        cur.execute(
            "DELETE FROM resumes WHERE id=%s AND user_id=%s",
            (resume_id, session['user_id'])
        )
        mysql.connection.commit()

    cur.close()
    return redirect('/resume')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
# ------------------HISTORY----------------
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT score, total_questions, date_taken
        FROM exam_attempts
        WHERE user_id=%s
        ORDER BY date_taken DESC
    """, (session['user_id'],))

    attempts = cur.fetchall()
    cur.close()

    return render_template('history.html', attempts=attempts)


if __name__ == "__main__":
    app.run(debug=True)