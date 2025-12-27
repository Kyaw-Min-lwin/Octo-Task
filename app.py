from flask import Flask, render_template, request, redirect, url_for, jsonify
from extensions import db
from flask_migrate import Migrate
import models
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from datetime import datetime, timezone  # <--- CHANGED: Added timezone

# this for the subtask generation
from ai_service import analyze_task
from services.scoring_service import predict_task_metrics, calculate_tmt_score

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)
migrate = Migrate(app, db)


@app.route("/", methods=["POST", "GET"])
def index():
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

            # 3. CREATE USER (If needed)
            user = models.User.query.first()
            if not user:
                user = models.User(
                    email="default@example.com",
                    username="default",
                    password_hash="dummy",
                )
                db.session.add(user)
                db.session.commit()

            # 4. SAVE TASK
            task = models.Task(
                user_id=user.id,
                title=task_title,
                priority_score=priority_score,
                status="pending",
                time_spent=0,  # Ensure it starts at 0, not None
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

    tasks = models.Task.query.order_by(models.Task.priority_score.desc()).all()
    return render_template("index.html", tasks=tasks)


@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json()
    text = data.get("title", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    metrics = predict_task_metrics(text)
    return jsonify(metrics)


@app.route("/api/calculate_score", methods=["POST"])
def api_calculate_score():
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
    # 1. STOP EVERYTHING ELSE
    user_id = 1
    active_task = models.Task.query.filter_by(status="active", user_id=user_id).first()

    # Current UTC time (Aware)
    now_utc = datetime.now(timezone.utc)

    if active_task and active_task.id != task_id:
        update_task_timer(task_id)

        active_task.status = "paused"

    # 2. START THE NEW TASK
    task = models.Task.query.get_or_404(task_id)
    task.status = "active"
    task.last_started_at = now_utc

    db.session.commit()
    return jsonify({"success": True, "status": "active"})


@app.route("/pause_task/<int:task_id>", methods=["POST"])
def pause_task(task_id):
    task = models.Task.query.get_or_404(task_id)
    update_task_timer(task)
    task.status = "paused"

    db.session.commit()
    return jsonify({"success": True, "status": "paused", "time_spent": task.time_spent})


@app.route("/complete_task/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    task = models.Task.query.get_or_404(task_id)
    now_utc = datetime.now(timezone.utc)

    update_task_timer(task)
    task.status = "completed"
    task.completed_at = now_utc

    db.session.commit()
    return jsonify({"success": True, "status": "completed"})


@app.route("/toggle_subtask/<int:subtask_id>", methods=["POST"])
def toggle_subtask(subtask_id):
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


if __name__ == "__main__":
    app.run(debug=True)
