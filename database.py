from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey, Float
from flask_login import UserMixin

# CREATE DATABASE BASE
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base, but DO NOT pass the 'app' yet
db = SQLAlchemy(model_class=Base)

# Configure tables
class Recording(db.Model):
    __tablename__ = "recordings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=True)
    duration: Mapped[str] = mapped_column(String(50), nullable=True)

    user = relationship('User', back_populates='recordings')
    comments = relationship('Comment', back_populates='recording')


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    last_name: Mapped[str] = mapped_column(String(250), nullable=False)
    user_type: Mapped[str] = mapped_column(String(250), nullable=False)
    website: Mapped[str] = mapped_column(Text, nullable=True)

    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    height_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)

    recordings = relationship('Recording', back_populates='user')
    comments = relationship('Comment', back_populates='user')

class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    recording_id: Mapped[int] = mapped_column(Integer, ForeignKey('recordings.id'), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    recording = relationship('Recording', back_populates='comments')
    user = relationship('User', back_populates='comments')
