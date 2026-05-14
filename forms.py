from flask_wtf import FlaskForm
from sqlalchemy import Numeric
from wtforms import StringField, SubmitField, PasswordField, SelectField
from wtforms.fields.numeric import FloatField, IntegerField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


# WTForm for creating a blog post
class CreateRecordingForm(FlaskForm):
    title = SelectField(
        "Select Activity Type",
        choices=[
            ('Sitting', 'Sitting'),('Standing', 'Standing')
            ,('Walking', 'Walking'),('Running', 'Running'),
            ('Exercising', 'Exercising'), ('Sleeping', 'Sleeping'),
            ('Swimming', 'Swimming')
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField("Start Recording")

class CommentForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")

# TODO: Create a RegisterForm to register new users
class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    age = IntegerField("Age", validators=[DataRequired()])
    height = IntegerField("Height", validators=[DataRequired()])
    weight = FloatField("Weight", validators=[DataRequired()])

    # FIXED: Added the 'choices' list so the dropdown actually has options
    user_type = SelectField(
        "Account Type",
        choices=[
            ('Regular User', 'Regular User'),
            ('Data Analyst', 'Data Analyst'),
            ('Admin', 'Admin')
        ],
        validators=[DataRequired()]
    )

    website = StringField("Website or Social Media (Optional)")

    submit = SubmitField("SIGN ME UP!")



# TODO: Create a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("LET ME IN!")

# TODO: Create a CommentForm so users can leave comments below Recordings
class CommentForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")

