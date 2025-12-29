from datetime import datetime, timezone
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    level = db.Column(db.Integer, default=1)
    total_xp = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    tasks = db.relationship("Task", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    status = db.Column(
        db.String(20), default="pending"
    )  # pending, active, paused, completed
    priority_score = db.Column(db.Float)

    # Time Tracking
    time_spent = db.Column(db.Integer, default=0)  # Total seconds focused
    last_started_at = db.Column(db.DateTime, nullable=True)

    # --- ADDED XP HISTORY FIELD ---
    xp_earned = db.Column(db.Integer, default=0)

    current_order = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime)

    subtasks = db.relationship("Subtask", backref="task", lazy=True)

    # --- ADDED RELATIONSHIP FOR TASK ANALYSIS ---
    # This allows `task.analysis.difficulty_score` to work
    analysis = db.relationship("TaskAnalysis", backref="task", uselist=False, lazy=True)


class TaskAnalysis(db.Model):
    __tablename__ = "task_analysis"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)

    urgency_score = db.Column(db.Float)
    fear_score = db.Column(db.Float)
    interest_score = db.Column(db.Float)

    difficulty_score = db.Column(db.Integer)  # Scale 1-10

    confidence = db.Column(db.Float)
    model_version = db.Column(db.String(50))

    analyzed_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


class Subtask(db.Model):
    __tablename__ = "subtasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)

    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)

    order_index = db.Column(db.Integer)
    status = db.Column(db.String(20), default="pending")

    estimated_effort = db.Column(db.Integer)
    created_by = db.Column(db.String(20))  # system / user / ai

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)


class TaskSession(db.Model):
    __tablename__ = "task_sessions"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    started_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    ended_at = db.Column(db.DateTime)

    active = db.Column(db.Boolean, default=True)
