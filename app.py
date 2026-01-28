# app.py (CLEANED & CONSOLIDATED)
import os
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
from helpers import make_qr_payload, generate_qr_image, verify_qr_payload, generate_certificate
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'devsecret')

ALLOWED_ADMIN_ROLES = {
    'Coordinator', 'Co-Coordinator', 'Co-Coordinator-Ops', 'Co-Coordinator-PR', 'Co-Coordinator-Finance'
}

# ----------------- Helpers -----------------

def get_user_by_email(email):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    u = cur.fetchone()
    cur.close(); conn.close()
    return u

def get_user_by_id(uid):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE user_id=%s", (uid,))
    u = cur.fetchone()
    cur.close(); conn.close()
    return u

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "danger")
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper

def role_required(allowed_roles):
    from functools import wraps
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if 'role' not in session or session['role'] not in allowed_roles:
                flash("Access denied: insufficient privileges.", "danger")
                return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ------------------ Routes ------------------

@app.route('/')
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT e.event_id, e.title, e.date, c.club_name
            FROM events e
            LEFT JOIN clubs c ON e.club_id = c.club_id
            WHERE e.date >= CURDATE()
            ORDER BY e.date ASC
            LIMIT 20
        """)
        upcoming_events = cur.fetchall()

        cur.execute("SELECT COUNT(*) AS total_clubs FROM clubs")
        club_row = cur.fetchone()
        club_count = club_row['total_clubs'] if club_row else 0
    finally:
        cur.close(); conn.close()

    user = get_user_by_id(session['user_id'])
    return render_template('dashboard.html',
                           events=upcoming_events,
                           club_count=club_count,
                           user=user,
                           active='dashboard')

# --------- Auth ----------
@app.route('/register', methods=['GET','POST'])
def register():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT club_id, club_name FROM clubs")
        clubs_list = cur.fetchall()
    finally:
        cur.close(); conn.close()

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        club_id = request.form.get('club_id') or None

        if not (name and email and password):
            flash("Name, email and password are required.", "danger")
            return render_template('register.html', clubs=clubs_list, user=None, active=None)

        pw_hash = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (name, email, password_hash, phone, club_id) VALUES (%s,%s,%s,%s,%s)",
                        (name, email, pw_hash, phone, club_id))
            conn.commit()
            flash("Registered successfully. Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash(f"Error registering user: {e}", "danger")
            return render_template('register.html', clubs=clubs_list, user=None, active=None)
        finally:
            cur.close(); conn.close()

    return render_template('register.html', clubs=clubs_list, user=None, active=None)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email'); pw = request.form.get('password')
        user = get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], pw):
            session['user_id'] = user['user_id']
            session['role'] = user.get('role')
            flash("Logged in successfully", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return render_template('login.html', user=None)
    return render_template('login.html', user=None)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for('login'))

# ---------- Clubs ----------
@app.route('/clubs')
@login_required
def clubs_list():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT 
                c.*,
                (SELECT img_path 
                 FROM club_images 
                 WHERE club_id = c.club_id 
                 ORDER BY img_id ASC LIMIT 1) AS first_image
            FROM clubs c
            ORDER BY c.club_name ASC
        """)
        clubs = cur.fetchall()
    finally:
        cur.close(); conn.close()

    user = get_user_by_id(session['user_id'])
    return render_template(
        "clubs_list.html",
        clubs=clubs,
        user=user,
        active="clubs"
    )

@app.route('/clubs/<int:club_id>')
@login_required
def club_details(club_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Fetch club details
        cur.execute("""
            SELECT c.*, u.name AS coordinator_name
            FROM clubs c
            LEFT JOIN users u ON c.coordinator_id = u.user_id
            WHERE c.club_id = %s
        """, (club_id,))
        club = cur.fetchone()

        # Fetch club images
        cur.execute("SELECT * FROM club_images WHERE club_id=%s", (club_id,))
        club_images = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    if not club:
        flash("Club not found!", "danger")
        return redirect('/clubs')

    return render_template(
        "club_details.html",
        club=club,
        club_images=club_images,
        user=get_user_by_id(session['user_id']),
        active='clubs'
    )


@app.route('/clubs/create', methods=['GET','POST'])
@login_required
def create_club():
    if request.method == 'POST':
        club_name = request.form.get('club_name')
        desc = request.form.get('description')
        coordinator_id = request.form.get('coordinator_id') or None
        if coordinator_id:
            try:
                coordinator_id = int(coordinator_id)
            except ValueError:
                coordinator_id = None

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO clubs (club_name, description, coordinator_id) VALUES (%s,%s,%s)",
                        (club_name, desc, coordinator_id))
            club_id = cur.lastrowid

            # MULTIPLE CLUB IMAGES
            image_files = request.files.getlist("club_images")

            for img in image_files:
                if img and img.filename:
                    filename = f"club_{club_id}_{int(time.time())}_{img.filename}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    img.save(save_path)

                    cur.execute("""
                        INSERT INTO club_images (club_id, img_path)VALUES (%s, %s)""", (club_id, f"uploads/{filename}"))

            conn.commit()
            flash("Club created", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error creating club: {e}", "danger")
        finally:
            cur.close(); conn.close()
        return redirect(url_for('clubs_list'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT user_id, name FROM users")
        users_for_select = cur.fetchall()
    finally:
        cur.close(); conn.close()

    user = get_user_by_id(session['user_id'])
    return render_template('create_club.html', users=users_for_select, user=user, active='clubs')

@app.route('/clubs/<int:club_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_club(club_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        if request.method == "POST":
            name = request.form['club_name']
            desc = request.form['description']

            # UPDATE CLUB
            cur.execute("""
                UPDATE clubs 
                SET club_name=%s, description=%s
                WHERE club_id=%s
            """, (name, desc, club_id))
            conn.commit()

            # HANDLE NEW IMAGE UPLOADS
            images = request.files.getlist("club_images")
            for img in images:
                if img and img.filename:
                    filename = f"club_{club_id}_{int(time.time())}_{img.filename}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    img.save(save_path)

                    cur.execute("""
                        INSERT INTO club_images (club_id, img_path)
                        VALUES (%s, %s)
                    """, (club_id, f"uploads/{filename}"))
                    conn.commit()

            flash("Club updated!", "success")
            return redirect(url_for('clubs_list'))

        # ---------- GET REQUEST ----------
        # fetch club
        cur.execute("SELECT * FROM clubs WHERE club_id=%s", (club_id,))
        club = cur.fetchone()

        # fetch images
        cur.execute("SELECT * FROM club_images WHERE club_id=%s", (club_id,))
        club_images = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    return render_template(
        "edit_club.html",
        club=club,
        club_images=club_images,
        user=get_user_by_id(session['user_id'])
    )

@app.route('/clubs/<int:club_id>/delete', methods=['POST'])
@login_required
def delete_club(club_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM clubs WHERE club_id=%s", (club_id,))
        conn.commit()
        flash("Club deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting club: {e}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for('clubs_list'))

# ---------- Venues ----------
@app.route('/venues')
@login_required
def venues():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM venues ORDER BY venue_name ASC")
        venues_list = cur.fetchall()
    finally:
        cur.close(); conn.close()
    user = get_user_by_id(session['user_id'])
    return render_template('venues.html', venues=venues_list, user=user, active='venues')

# ---------- Events ----------
@app.route('/events')
@login_required
def events_list():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT 
            e.*,
            c.club_name,
            c.description,
            v.venue_name,
            (SELECT img_path FROM event_images WHERE event_id = e.event_id LIMIT 1) AS first_image
            FROM events e
            LEFT JOIN clubs c ON e.club_id = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            ORDER BY e.date ASC
            """)
        events = cur.fetchall()

    finally:
        cur.close(); conn.close()

    user = get_user_by_id(session['user_id'])
    return render_template("events_list.html", events=events, user=user, active="events")

@app.route('/events/<int:event_id>')
@login_required
def event_detail(event_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # event with club description + venue
        cur.execute("""
            SELECT e.*, c.club_name, c.description, v.venue_name
            FROM events e
            LEFT JOIN clubs c ON e.club_id = c.club_id
            LEFT JOIN venues v ON e.venue_id = v.venue_id
            WHERE e.event_id = %s
        """, (event_id,))
        event = cur.fetchone()

        # fetch event images
        cur.execute("SELECT * FROM event_images WHERE event_id=%s", (event_id,))
        event_images = cur.fetchall()


        if not event:
            flash("Event not found", "danger")
            return redirect(url_for('events_list'))

        # resources for event
        cur.execute("""
            SELECT r.resource_name, er.quantity
            FROM event_resources er
            JOIN resources r ON r.resource_id = er.resource_id
            WHERE er.event_id = %s
        """, (event_id,))
        event_resources = cur.fetchall()
    finally:
        cur.close(); conn.close()

    user = get_user_by_id(session['user_id'])
    return render_template('event_details.html', event=event, event_resources=event_resources, event_images=event_images, user=user, active='events')

@app.route('/events/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == "POST":
        club_id = request.form.get('club_id')
        title = request.form.get('title')
        description = request.form.get('description')
        event_lead = request.form.get('event_lead')
        contact_no = request.form.get('contact_no')
        venue_id = request.form.get('venue_id')
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        registration_link = request.form.get('registration_link')

        # Validate club_id if provided
        try:
            club_id = int(club_id) if club_id else None
        except:
            flash("Invalid club selection.", "danger")
            return redirect(url_for('create_event'))

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        try:
            # check venue conflict
            cur.execute("""
                SELECT * FROM events
                WHERE venue_id=%s AND date=%s 
                  AND (
                        (start_time <= %s AND end_time >= %s)
                    OR  (start_time <= %s AND end_time >= %s)
                  )
            """, (venue_id, date, start_time, start_time, end_time, end_time))
            conflict = cur.fetchall()
            if conflict:
                flash("⚠ This venue is already booked for the selected time!", "danger")
                return redirect(url_for('create_event'))

            # insert
            cur.execute("""
                INSERT INTO events
                (club_id, title, description, event_lead, contact_no,
                 venue_id, date, start_time, end_time, registration_link, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (club_id, title, description, event_lead, contact_no,
                  venue_id, date, start_time, end_time, registration_link, session['user_id']))
            
            event_id = cur.lastrowid  # newly created event ID

            # MULTIPLE EVENT IMAGES
            image_files = request.files.getlist("event_images")

            for img in image_files:
                if img and img.filename:
                    filename = f"event_{event_id}_{int(time.time())}_{img.filename}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    img.save(save_path)

                    cur.execute("""
                        INSERT INTO event_images (event_id, img_path)VALUES (%s, %s)""", (event_id, f"uploads/{filename}"))


            conn.commit()
            flash("Event created successfully!", "success")
            return redirect(url_for('events_list'))
        except Exception as e:
            conn.rollback()
            flash(f"Error creating event: {e}", "danger")
            return redirect(url_for('create_event'))
        finally:
            cur.close(); conn.close()

    # GET -> render form with clubs + venues
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT club_id, club_name FROM clubs ORDER BY club_name")
        clubs_list = cur.fetchall()
        cur.execute("SELECT venue_id, venue_name FROM venues ORDER BY venue_name")
        venues_list = cur.fetchall()
    finally:
        cur.close(); conn.close()

    user = get_user_by_id(session['user_id'])
    return render_template("create_event.html", clubs=clubs_list, venues=venues_list, user=user, active="events")

@app.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # ------------------------------- POST: Update Event -------------------------------
        if request.method == "POST":
            club_id = request.form.get('club_id')
            title = request.form.get('title')
            description = request.form.get('description')
            event_lead = request.form.get('event_lead')
            contact_no = request.form.get('contact_no')
            venue_id = request.form.get('venue_id')
            date = request.form.get('date')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            registration_link = request.form.get('registration_link')

            # Update event record
            cur2 = conn.cursor()
            cur2.execute("""
                UPDATE events
                SET club_id=%s, title=%s, description=%s, event_lead=%s, contact_no=%s,
                    venue_id=%s, date=%s, start_time=%s, end_time=%s, registration_link=%s
                WHERE event_id=%s
            """, (club_id, title, description, event_lead, contact_no,
                  venue_id, date, start_time, end_time, registration_link, event_id))
            conn.commit()
            cur2.close()

            # ------------------------------- Upload New Images -------------------------------
            image_files = request.files.getlist("event_images")
            cur3 = conn.cursor()

            for img in image_files:
                if img and img.filename.strip() != "":
                    filename = f"event_{event_id}_{int(time.time())}_{img.filename}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    img.save(save_path)

                    cur3.execute("""
                        INSERT INTO event_images (event_id, img_path)
                        VALUES (%s, %s)
                    """, (event_id, f"uploads/{filename}"))

            conn.commit()
            cur3.close()

            flash("Event updated successfully!", "success")
            return redirect(url_for('edit_event', event_id=event_id))

        # ------------------------------- GET: Fetch event details -------------------------------
        cur.execute("SELECT * FROM events WHERE event_id=%s", (event_id,))
        event = cur.fetchone()

        cur.execute("SELECT club_id, club_name FROM clubs ORDER BY club_name")
        clubs = cur.fetchall()

        cur.execute("SELECT venue_id, venue_name FROM venues ORDER BY venue_name")
        venues = cur.fetchall()

        cur.execute("SELECT * FROM event_images WHERE event_id=%s", (event_id,))
        event_images = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    return render_template(
        "edit_event.html",
        event=event,
        clubs=clubs,
        venues=venues,
        event_images=event_images,
        user=get_user_by_id(session['user_id']),
        active="events"
    )

@app.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM events WHERE event_id=%s", (event_id,))
        conn.commit()
        flash("Event deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting event: {e}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for('events_list'))

# ---------- Resources ----------
@app.route('/resources')
@login_required
def resources_list():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT 
                r.resource_id,
                r.resource_name,
                r.total_quantity,
                r.description,
                IFNULL(SUM(er.quantity), 0) AS allocated
            FROM resources r
            LEFT JOIN event_resources er ON r.resource_id = er.resource_id
            GROUP BY r.resource_id, r.resource_name, r.total_quantity, r.description
            ORDER BY r.resource_name;
        """)
        resources = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return render_template(
        "resources.html",
        resources=resources,
        user=get_user_by_id(session['user_id']),
        active="resources"
    )

@app.route('/clubs/<int:club_id>/delete_image/<int:img_id>', methods=['POST'])
@login_required
def delete_club_image(club_id, img_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Get file path
        cur.execute("SELECT img_path FROM club_images WHERE img_id=%s", (img_id,))
        img = cur.fetchone()

        if img:
            file_path = os.path.join(app.static_folder, img['img_path'])
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete from DB
        cur.execute("DELETE FROM club_images WHERE img_id=%s", (img_id,))
        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

    finally:
        cur.close(); conn.close()

@app.route('/events/<int:event_id>/delete_image/<int:img_id>', methods=['POST'])
@login_required
def delete_event_image(event_id, img_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # Get image path
        cur.execute("SELECT img_path FROM event_images WHERE img_id=%s AND event_id=%s",
                    (img_id, event_id))
        img = cur.fetchone()

        if not img:
            flash("Image not found.", "danger")
            return redirect(url_for('edit_event', event_id=event_id))

        # Delete from DB
        cur.execute("DELETE FROM event_images WHERE img_id=%s", (img_id,))
        conn.commit()

        # Delete file
        import os
        full_path = os.path.join("static", img["img_path"])
        if os.path.exists(full_path):
            os.remove(full_path)

        flash("Image deleted successfully!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error deleting image: {e}", "danger")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for('edit_event', event_id=event_id))

# ---------- Recommendations ----------
@app.route('/recommendations')
@login_required
def recommendations():
    uid = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT e.club_id, COUNT(1) as cnt
            FROM attendance a
            JOIN events e ON a.event_id = e.event_id
            WHERE a.user_id=%s
            GROUP BY e.club_id
            ORDER BY cnt DESC
            LIMIT 3
        """, (uid,))
        clubs_rel = cur.fetchall()
        club_ids = [str(c['club_id']) for c in clubs_rel]
        if club_ids:
            q = ("SELECT e.*, c.club_name "
                 "FROM events e JOIN clubs c ON e.club_id=c.club_id "
                 "WHERE e.club_id IN (" + ",".join(club_ids) + ") "
                 "AND e.date >= CURDATE() ORDER BY e.date LIMIT 10")
            cur.execute(q)
            recs = cur.fetchall()
        else:
            cur.execute("SELECT e.*, c.club_name FROM events e JOIN clubs c ON e.club_id=c.club_id WHERE e.date >= CURDATE() ORDER BY e.date LIMIT 10")
            recs = cur.fetchall()
    finally:
        cur.close(); conn.close()

    user = get_user_by_id(session['user_id'])
    return render_template('recommendations.html', events=recs, user=user, active='recommendations')

# ---------- Error handlers ----------
@app.errorhandler(404)
def not_found(e):
    user = get_user_by_id(session['user_id']) if 'user_id' in session else None
    return render_template('404.html', user=user), 404

@app.errorhandler(500)
def server_error(e):
    user = get_user_by_id(session['user_id']) if 'user_id' in session else None
    return render_template('500.html', user=user), 500

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


if __name__ == '__main__':
    app.run(debug=True)
