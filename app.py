from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    session,
    flash,
)
from extensions import db
from flask_migrate import Migrate
import models
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from datetime import datetime, timezone  # <--- CHANGED: Added timezone
import os

# this for the subtask generation
from ai_service import analyze_task
from services.scoring_service import predict_task_metrics, calculate_tmt_score

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "octo_command_secret_key_999")
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)
migrate = Migrate(app, db)


# --- AUTH ROUTES ---


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        if not username or not password:
            flash("CREDENTIALS MISSING", "error")
            return redirect(url_for("register"))

        if models.User.query.filter_by(username=username).first():
            flash("CALL SIGN ALREADY TAKEN", "error")
            return redirect(url_for("register"))

        # Create Secure User
        new_user = models.User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Auto-login after register
        session["user_id"] = new_user.id
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        user = models.User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            return redirect(url_for("index"))
        else:
            flash("INVALID CREDENTIALS", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


@app.route("/", methods=["POST", "GET"])
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = models.User.query.get(session["user_id"])
    if not user:
        session.pop("user_id", None)
        return redirect(url_for("login"))
    if request.method == "POST":
        task_title = request.form.get("task_title")

        # 1. GET SLIDER VALUES
        try:
            urgency = float(request.form.get("urgency", 5.0))
            fear = float(request.form.get("fear", 5.0))
            interest = float(request.form.get("interest", 5.0))
        except ValueError:
            urgency, fear, interest = 5.0, 5.0, 5.0

        if task_title:
            priority_score = compute_final_priority(urgency, fear, interest)

            # 4. SAVE TASK
            task = models.Task(
                user_id=user.id,
                title=task_title,
                priority_score=priority_score,
                status="pending",
                time_spent=0,
            )
            db.session.add(task)
            db.session.commit()

            # 5. GET SUBTASKS
            ai_data = analyze_task(task_title)
            breakdown_steps = ai_data.get("breakdown", [])
            ai_difficulty = ai_data.get("difficulty", 0)

            # 2. If AI returns 0 (unsure), fallback to the user's Fear score
            final_difficulty = ai_difficulty if ai_difficulty > 0 else fear

            for index, step_text in enumerate(breakdown_steps):
                subtask = models.Subtask(
                    task_id=task.id,
                    title=step_text,
                    order_index=index,
                    status="pending",
                    created_by="gemini",
                )
                db.session.add(subtask)

            # 6. SAVE ANALYSIS
            analysis = models.TaskAnalysis(
                task_id=task.id,
                urgency_score=urgency,
                fear_score=fear,
                interest_score=interest,
                difficulty_score=final_difficulty,
                confidence=1.0,
                model_version="MiniLM-L6-v2",
            )
            db.session.add(analysis)
            db.session.commit()

        return redirect(url_for("index"))

    #  GET Tasks (Filtered by User)
    tasks = (
        models.Task.query.filter_by(user_id=user.id)
        .order_by(models.Task.priority_score.desc())
        .all()
    )
    tasks_data = []
    for t in tasks:
        tasks_data.append(
            {
                "id": t.id,
                "title": t.title,
                "priority": t.priority_score or 0,
                "status": t.status,
                "diff": t.analysis.difficulty_score if t.analysis else 5,
                "subtasks": [
                    {"id": s.id, "title": s.title, "status": s.status}
                    for s in t.subtasks
                ],
                "start": t.last_started_at.isoformat() if t.last_started_at else None,
                "accumulated": t.time_spent or 0,
            }
        )

    # 2. Pass the single clean list to the template
    return render_template("index.html", tasks=tasks, tasks_json=tasks_data, user=user)


@app.route("/api/predict", methods=["POST"])
def predict():
    if "user_id" not in session:
        return redirect(url_for("login"))
    data = request.get_json()
    text = data.get("title", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    metrics = predict_task_metrics(text)
    return jsonify(metrics)


@app.route("/api/calculate_score", methods=["POST"])
def api_calculate_score():
    if "user_id" not in session:
        return redirect(url_for("login"))
    data = request.get_json()
    u = float(data.get("urgency", 5))
    f = float(data.get("fear", 5))
    i = float(data.get("interest", 5))

    # REFACTORED: Single line call
    priority_score = compute_final_priority(u, f, i)

    return jsonify({"priority_score": priority_score})


# --- HELPER FUNCTIONS ---


def compute_final_priority(urgency, fear, interest):
    """
    Centralizes the priority score math.
    Change the formula here, and it updates everywhere.
    """
    impulsiveness = 1.5
    tmt_score = calculate_tmt_score(urgency, fear, interest, impulsiveness)

    priority_pressure = urgency * 2 + fear
    # Weight: 60% Pressure, 40% Procrastination (TMT)
    final_priority = priority_pressure * 0.6 + tmt_score * 0.4
    return final_priority


def update_task_timer(task):
    """Updates time_spent based on last_started_at."""
    if task.status == "active" and task.last_started_at:
        now_utc = datetime.now(timezone.utc)
        start_time = task.last_started_at

        # Ensure UTC consistency
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        delta = (now_utc - start_time).total_seconds()

        # Update time
        current_time = task.time_spent or 0
        task.time_spent = current_time + int(delta)

        # Reset start time
        task.last_started_at = None


@app.route("/start_task/<int:task_id>", methods=["POST"])
def start_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    # 1. STOP EVERYTHING ELSE
    user_id = session["user_id"]
    active_task = models.Task.query.filter_by(status="active", user_id=user_id).first()

    # Current UTC time (Aware)
    now_utc = datetime.now(timezone.utc)

    if active_task and active_task.id != task_id:
        update_task_timer(active_task)

        active_task.status = "paused"

    # 2. START THE NEW TASK
    task = models.Task.query.get_or_404(task_id)
    task.status = "active"
    task.last_started_at = now_utc

    db.session.commit()
    return jsonify({"success": True, "status": "active"})


@app.route("/pause_task/<int:task_id>", methods=["POST"])
def pause_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    task = models.Task.query.get_or_404(task_id)
    update_task_timer(task)
    task.status = "paused"

    db.session.commit()
    return jsonify({"success": True, "status": "paused", "time_spent": task.time_spent})


@app.route("/complete_task/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    task = models.Task.query.get_or_404(task_id)
    user = models.User.query.get(task.user_id)  # Get the user
    now_utc = datetime.now(timezone.utc)

    # 1. Final Timer Update
    update_task_timer(task)

    # 2. Status Update
    task.status = "completed"
    task.completed_at = now_utc

    # 3. --- NEW: CALCULATE XP ---
    # Formula: 10 XP per minute of focus + Bonus for Priority
    minutes_focused = (task.time_spent or 0) / 60
    base_xp = minutes_focused * 10

    # Priority Multiplier: Higher priority = More XP (Max 2x multiplier)
    multiplier = 1 + (task.priority_score / 100)

    xp_gained = int(base_xp * multiplier) + 50  # +50 flat bonus for finishing

    # Save to User (Assuming you added total_xp to User model previously)
    if not user.total_xp:
        user.total_xp = 0
    user.total_xp += xp_gained

    # Save to Task for history
    task.xp_earned = xp_gained

    # Check for Level Up (Simple logic: Level = sqrt(XP)/10 or similar)
    # For hackathon: Just strict thresholds
    old_level = user.level or 1
    new_level = int(1 + (user.total_xp / 1000))  # Level up every 1000 XP
    leveled_up = new_level > old_level
    user.level = new_level

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "status": "completed",
            "xp_gained": xp_gained,
            "total_xp": user.total_xp,
            "leveled_up": leveled_up,
            "new_level": new_level,
        }
    )


@app.route("/toggle_subtask/<int:subtask_id>", methods=["POST"])
def toggle_subtask(subtask_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    sub = models.Subtask.query.get_or_404(subtask_id)

    # Toggle status
    if sub.status == "completed":
        sub.status = "pending"
        sub.completed_at = None
    else:
        sub.status = "completed"
        sub.completed_at = datetime.now(timezone.utc)

    db.session.commit()
    return jsonify({"success": True, "status": sub.status})


@app.route("/recommend_switch/<int:current_task_id>", methods=["GET"])
def recommend_switch(current_task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    # Query for BOTH Task and TaskAnalysis
    result = (
        db.session.query(models.Task, models.TaskAnalysis)  # Select both
        .join(models.TaskAnalysis, models.Task.id == models.TaskAnalysis.task_id)
        .filter(
            models.Task.id != current_task_id,
            models.Task.status.in_(["pending", "paused", "active"]),
            models.TaskAnalysis.difficulty_score <= 6,
        )
        .order_by(models.TaskAnalysis.interest_score.desc())
        .first()
    )

    if result:
        # Unpack the tuple (Task, TaskAnalysis)
        task, analysis = result

        return jsonify(
            {
                "found": True,
                # Now use 'task' for title and 'analysis' for score
                "message": f"How about '{task.title}'? It's fairly easy (Diff: {analysis.difficulty_score}) and might help you reset.",
                "task_id": task.id,
            }
        )
    else:
        return jsonify(
            {
                "found": False,
                "message": "No suitable tasks found. Time for a break?",
            }
        )


@app.route("/focus/<int:task_id>")
def focus_view(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    task = models.Task.query.get_or_404(task_id)

    # Serialize just this SINGLE task for the JavaScript
    task_data = {
        "id": task.id,
        "title": task.title,
        "priority": task.priority_score or 0,
        "status": task.status,
        "diff": task.analysis.difficulty_score if task.analysis else 5,
        "subtasks": [
            {"id": s.id, "title": s.title, "status": s.status} for s in task.subtasks
        ],
        "start": task.last_started_at.isoformat() if task.last_started_at else None,
        "accumulated": task.time_spent or 0,
    }

    return render_template("focus.html", task_json=task_data)


# ... existing imports ...

if __name__ == "__main__":
    # Remove this block later if you want strict migrations
    with app.app_context():
        db.create_all()
        print("Tables created successfully.")

    app.run(debug=True, port=7860)
