import json
from datetime import date, datetime
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor, CKEditorField
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user, UserMixin
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from analyze import process_sensor_data
# Import the MQTT Receiver Class
from logger import MQTTReceiver

# Import the Database components
from database import db, Recording, User, Comment

# Import forms from the forms.py
from forms import CreateRecordingForm, RegisterForm, LoginForm, CommentForm
import os




'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''
# Initialize the Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)


# Initialize Gravatar
gravatar = Gravatar(app,
                    size=100,  # Default size for the avatar images
                    rating='g',  # Gravatar rating
                    default='retro',  # Default image if no Gravatar found
                    force_default=False,  # Force default avatar
                    force_lower=False,  # Force email to lowercase
                    use_ssl=True,  # Use HTTPS for Gravatar URLs
                    base_url=None)  # Optional base URL


active_sessions = {}  # A dictionary to hold individual user streams


# Initiate Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# TODO: Configure Flask-Login
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///recordings.db")
db.init_app(app)


with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        name = request.form.get('name').title()
        last_name = request.form.get('last_name').title()
        email = request.form.get('email')
        weight_kg = request.form.get('weight', type=float)
        height_cm = request.form.get('height', type=int)
        age = request.form.get('age', type=int)

        user_type = request.form.get('user_type')
        website = request.form.get('website')

        # Note, email in db is unique so will only have one result.
        user = User.query.filter_by(email=email).first()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )

        # ADDED: Pass weight_kg and height_cm to the User instantiation
        new_user = User(
            name=name,
            email=email,
            password=hash_and_salted_password,
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            last_name=last_name,
            user_type=user_type,
            website=website
        )

        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_recordings'))

    return render_template("register.html", form=form)


# TODO: Retrieve a user from the database based on their email.
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Find user by email
        user = User.query.filter_by(email=email).first()

        # Check if user exists and if the password is correct
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('get_all_recordings'))
        elif user:
            flash('Login failed. Check your email and/or password.', 'danger')

        else:
            flash('Account does not exist. Please register!', 'danger')

    return render_template("login.html", form=form)

def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Check if the current user is an admin (e.g., user ID == 1)
        if current_user.is_authenticated and current_user.id == 1:
            return func(*args, **kwargs)  # Call the original function if authenticated and admin
        else:
            return abort(403, description="Access to this resource is forbidden. You do not have the necessary permissions.")
    return decorated_function  # Return the decorated function

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/')
def get_all_recordings():
    # Fetch all recordings from the database
    result = db.session.execute(db.select(Recording))
    recordings = result.scalars().all()

    return render_template("index.html", recordings=recordings)

@app.route('/older_recordings')
def get_older_recordings():
    # Fetch all recordings from the database
    result = db.session.execute(db.select(Recording))
    recordings = result.scalars().all()

    return render_template("older_recordings.html", recordings=recordings)

@app.route("/record/<int:recording_id>", methods=["GET", "POST"])
def show_recording(recording_id):
    # 1. Fetch the specific recording
    record = db.get_or_404(Recording, recording_id)
    comment_form = CommentForm()

    total_points, sensor_stats = process_sensor_data(record.data)
    # 2. Handle Form Submission
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=comment_form.comment.data,
                recording_id=recording_id,
                user_id=current_user.id
            )
            db.session.add(new_comment)
            db.session.commit()
            # Redirect back to the SAME page so they see their comment
            return redirect(url_for('show_recording', recording_id=recording_id))
        else:
            flash("You need to login in order to be able to comment!")
            return redirect(url_for('login'))


    # The template can access record.comments directly.
    return render_template("record.html", record=record, comment=comment_form,
                           total_points=total_points,
                           sensor_stats=sensor_stats)

# TODO: Use a decorator so a user can create a new recoding
@app.route("/new-recording", methods=["GET", "POST"])
def add_new_recording():
    form = CreateRecordingForm()
    if form.validate_on_submit():
        user_id = current_user.id

        # 1. Only create a new listener if the user doesn't already have one running in the background
        if user_id not in active_sessions:
            active_sessions[user_id] = MQTTReceiver(broker_ip="localhost", topic="#")

        # 2. Start appending data (flips the boolean to True)
        active_sessions[user_id].start_recording()

        # 3. Create the database entry (leaving 'data' empty for now)
        new_recording = Recording(
            title=form.title.data,
            user_id=current_user.id,
            author=db.get_or_404(User, current_user.id).name + ' ' + db.get_or_404(User, current_user.id).last_name,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_recording)
        db.session.commit()

        # 4. Pass the new recording's ID to the template
        return render_template("recording.html", recording_id=new_recording.id)
    return render_template("make-recording.html", form=form)


@app.route("/end-recording/<int:recording_id>", methods=["GET", "POST"])
def end_recording(recording_id):
    user_id = current_user.id

    # 1. Fetch the recording AND verify ownership immediately
    recording_to_update = db.get_or_404(Recording, recording_id)
    if recording_to_update.user_id != user_id:
        abort(403, description="You do not have permission to modify this recording.")

    # 2. Check if they have an active session
    if user_id in active_sessions:
        # Stop capturing data (flips the boolean to False) and retrieve it
        recorded_data, recording_duration = active_sessions[user_id].stop_recording()

        # WE DO NOT DELETE active_sessions[user_id] ANYMORE.
        # It stays alive in the background waiting for the next recording.
    else:
        recorded_data, recording_duration = [], "00:00:00"

    # 3. Save the duration and data to the database
    recording_to_update.duration = recording_duration

    if recorded_data:
        recording_to_update.data = json.dumps(recorded_data)
    else:
        recording_to_update.data = "No data captured."

    db.session.commit()

    flash("Recording ended successfully!", "success")
    return redirect(url_for('show_recording', recording_id=recording_to_update.id))


@app.route("/edit_account/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_account(user_id):
    user_to_edit = db.get_or_404(User, user_id)

    # Pre-populate the form with the user's current data so the boxes aren't empty
    edit_form = RegisterForm(
        name=user_to_edit.name,
        last_name=user_to_edit.last_name,
        email=user_to_edit.email,
        age=user_to_edit.age,
        weight=user_to_edit.weight_kg,
        height=user_to_edit.height_cm,
        user_type=user_to_edit.user_type,
        website=user_to_edit.website
    )

    edit_form.submit.label.text = "SAVE CHANGES"

    if edit_form.validate_on_submit():
        # Pull the data directly from the validated WTForm
        user_to_edit.name = edit_form.name.data
        user_to_edit.last_name = edit_form.last_name.data
        user_to_edit.email = edit_form.email.data
        user_to_edit.age = edit_form.age.data
        user_to_edit.weight_kg = edit_form.weight.data
        user_to_edit.height_cm = edit_form.height.data
        user_to_edit.user_type = edit_form.user_type.data
        user_to_edit.website = edit_form.website.data

        # Hash the new password before saving
        if edit_form.password.data:  # Only update if the field is not empty
            user_to_edit.password = generate_password_hash(
                edit_form.password.data,
                method='pbkdf2:sha256',
                salt_length=8
            )

        db.session.commit()

        # Redirect them back to their clean account page
        return redirect(url_for("account", name=user_to_edit.name, last_name=user_to_edit.last_name))

    return render_template("edit_account.html", form=edit_form)

@app.route("/edit_recording/<int:recording_id>", methods=["GET", "POST"])
def edit_recording(recording_id):
    recording_to_edit = db.get_or_404(Recording, recording_id)

    # Pre-populate the form with the recording's current data so the boxes aren't empty
    edit_form = CreateRecordingForm(
        title=recording_to_edit.title
    )

    edit_form.title.label.text = "Edit Activity Type"
    edit_form.submit.label.text = "SAVE CHANGES"

    if edit_form.validate_on_submit():
        # Pull the data directly from the validated WTForm
        recording_to_edit.title = edit_form.title.data
        db.session.commit()

        # Redirect them back to their clean recording page
        return redirect(url_for("show_recording", recording_id=recording_id))

    return render_template("edit_recording.html", form=edit_form)

# TODO: Use a decorator so only an admin or the author can delete a post


@app.route("/delete/<int:recording_id>", methods=["GET", "POST"])
def delete_recording(recording_id):
    recording_to_delete = db.get_or_404(Recording, recording_id)
    db.session.delete(recording_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_recordings'))


@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    comment_to_delete = db.get_or_404(Comment, comment_id)
    db.session.delete(comment_to_delete)
    recording_id = comment_to_delete.recording_id
    db.session.commit()
    return redirect(url_for('show_recording', recording_id=recording_id))


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/recording")
def recording():
    return render_template("recording.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/account/<name>_<last_name>")
def account(name, last_name):
    name = current_user.name
    height = current_user.height_cm
    weight = current_user.weight_kg
    age = current_user.age
    last_name = current_user.last_name
    user_type = current_user.user_type
    id = current_user.id
    website = current_user.website
    return render_template("account.html", name=name, height=height,
                           weight=weight, last_name=last_name, age=age,
                           user_type=user_type, id=id, website=website)




if __name__ == "__main__":
    app.run(debug=True, port=5002)


