
from datetime import datetime
from extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship("Task", backref="user", lazy=True)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    status = db.Column(db.String(20), default="pending")
    priority_score = db.Column(db.Float)
    current_order = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    subtasks = db.relationship("Subtask", backref="task", lazy=True)


class TaskAnalysis(db.Model):
    __tablename__ = "task_analysis"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)

    urgency_score = db.Column(db.Float)
    fear_score = db.Column(db.Float)
    interest_score = db.Column(db.Float)

    confidence = db.Column(db.Float)
    model_version = db.Column(db.String(50))

    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

class TaskScore(db.Model):
    __tablename__ = "task_scores"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)

    final_score = db.Column(db.Float, nullable=False)
    formula_version = db.Column(db.String(50))

    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Subtask(db.Model):
    __tablename__ = "subtasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    order_index = db.Column(db.Integer)
    status = db.Column(db.String(20), default="pending")

    estimated_effort = db.Column(db.Integer)
    created_by = db.Column(db.String(20))  # system / user / ai

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


class TaskSession(db.Model):
    __tablename__ = "task_sessions"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)

    active = db.Column(db.Boolean, default=True)

class ProgressLog(db.Model):
    __tablename__ = "progress_logs"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    subtask_id = db.Column(db.Integer, db.ForeignKey("subtasks.id"))

    progress_type = db.Column(db.String(20))  # checkpoint / partial / completed
    note = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    type = db.Column(db.String(50))
    message = db.Column(db.Text)
    read = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)