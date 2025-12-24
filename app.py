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
            # 2. CALCULATE SCORE
            impulsiveness = 1.5
            final_score = calculate_tmt_score(urgency, fear, interest, impulsiveness)
            priority_pressure = urgency * 2 + fear
            priority_score = priority_pressure * 0.6 + final_score * 0.4

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

            # 5. SAVE ANALYSIS
            analysis = models.TaskAnalysis(
                task_id=task.id,
                urgency_score=urgency,
                fear_score=fear,
                interest_score=interest,
                confidence=1.0,
                model_version="MiniLM-L6-v2",
            )
            db.session.add(analysis)

            # 6. GET SUBTASKS
            ai_data = analyze_task(task_title)
            breakdown_steps = ai_data.get("breakdown", [])

            for index, step_text in enumerate(breakdown_steps):
                subtask = models.Subtask(
                    task_id=task.id,
                    title=step_text,
                    order_index=index,
                    status="pending",
                    created_by="gemini",
                )
                db.session.add(subtask)

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

    # Get values, defaulting to 5.0
    u = float(data.get("urgency", 5))
    f = float(data.get("fear", 5))
    i = float(data.get("interest", 5))

    # Use the EXACT same formula as the backend
    impulsiveness = 1.5
    score = calculate_tmt_score(u, f, i, impulsiveness)
    priority_pressure = u * 2 + f
    priority_score = priority_pressure * 0.6 + score * 0.4

    return jsonify({"priority_score": priority_score})


@app.route("/start_task/<int:task_id>", methods=["POST"])
def start_task(task_id):
    # 1. STOP EVERYTHING ELSE
    user_id = 1
    active_task = models.Task.query.filter_by(status="active", user_id=user_id).first()

    # Current UTC time (Aware)
    now_utc = datetime.now(timezone.utc)

    if active_task and active_task.id != task_id:
        if active_task.last_started_at:
            # Ensure last_started_at is treated as UTC
            start_time = active_task.last_started_at
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)

            delta = (now_utc - start_time).total_seconds()
            # Safety: Treat None as 0
            current_time = active_task.time_spent or 0
            active_task.time_spent = current_time + int(delta)

        active_task.status = "paused"
        active_task.last_started_at = None

    # 2. START THE NEW TASK
    task = models.Task.query.get_or_404(task_id)
    task.status = "active"
    task.last_started_at = now_utc

    db.session.commit()
    return jsonify({"success": True, "status": "active"})


@app.route("/pause_task/<int:task_id>", methods=["POST"])
def pause_task(task_id):
    task = models.Task.query.get_or_404(task_id)
    now_utc = datetime.now(timezone.utc)

    if task.status == "active" and task.last_started_at:
        start_time = task.last_started_at
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        delta = (now_utc - start_time).total_seconds()

        current_time = task.time_spent or 0
        task.time_spent = current_time + int(delta)

    task.status = "paused"
    task.last_started_at = None

    db.session.commit()
    return jsonify({"success": True, "status": "paused", "time_spent": task.time_spent})


@app.route("/complete_task/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    task = models.Task.query.get_or_404(task_id)
    now_utc = datetime.now(timezone.utc)

    if task.status == "active" and task.last_started_at:
        start_time = task.last_started_at
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        delta = (now_utc - start_time).total_seconds()

        current_time = task.time_spent or 0
        task.time_spent = current_time + int(delta)

    task.status = "completed"
    task.last_started_at = None
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
    current_task = models.Task.query.get(current_task_id)
    recovery_task = (
        models.Task.query.join(models.TaskAnalysis)
        .filter(
            models.Task.id != current_task_id,
            models.Task.status == "pending",
            models.TaskAnalysis.fear_score < 5.0,
            models.TaskAnalysis.interest_score > 6.0,
        )
        .order_by(models.TaskAnalysis.urgency_score.desc())
        .first()
    )

    if recovery_task:
        return jsonify(
            {
                "found": True,
                "message": f"You seem stuck. Let's switch to '{recovery_task.title}' for a dopamine hit?",
                "task_id": recovery_task.id,
            }
        )
    else:
        return jsonify(
            {
                "found": False,
                "message": "No easy tasks found. Maybe take a 5-minute walk?",
            }
        )


if __name__ == "__main__":
    app.run(debug=True)
