from datetime import datetime
from BrainBoost import db, login_manager
from flask_login import UserMixin

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    email = db.Column(db.String(125), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    history_record = db.relationship("HistoryRecord", backref="owner", lazy=True)

    def __repr__(self):
        return f"User('{self.id}','{self.username}', '{self.email}')"


class HistoryRecord(db.Model):
    __tablename__ = "history_record"
    file_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(150), nullable=False)
    # processing_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", name="fk_user_id"), nullable=False)
    generated_flashcards = db.relationship("Flashcard", backref="file", lazy=True)

    def __repr__(self):
        return f"HistoryRecord('{self.file_id}','{self.file_name}', '{self.user_id}')"


# update**********************888
class Flashcard(db.Model):
    __tablename__ = "flashcard"
    flashcard_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(150), nullable=False)
    choice1 = db.Column(db.String(150), nullable=False)
    choice2 = db.Column(db.String(150), nullable=False)
    choice3 = db.Column(db.String(150), nullable=False)
    choice4 = db.Column(db.String(150), nullable=False)

    right_answer = db.Column(db.String(50), nullable=False)
    saved_answer = db.Column(db.Boolean, nullable=False, default=True)
    file_id = db.Column(db.Integer, db.ForeignKey("history_record.file_id", ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return f"Flashcard('{self.flashcard_id}','{self.question}','{self.right_answer}','{self.file_id}')"
