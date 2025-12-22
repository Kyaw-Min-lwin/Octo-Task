from flask import Flask, render_template, request, redirect, url_for, jsonify
from extensions import db
from flask_migrate import Migrate
import models
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
import random

# Keep this for the subtask generation
from ai_service import analyze_task

# Import your new logic
from services.scoring_service import predict_task_metrics, calculate_tmt_score

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)
migrate = Migrate(app, db)  # Ensure migration is linked


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        task_title = request.form.get("task_title")

        # 1. GET SLIDER VALUES (Trust the User/Frontend)
        # We default to 5.0 if something goes wrong
        try:
            urgency = float(request.form.get("urgency", 5.0))
            fear = float(request.form.get("fear", 5.0))
            interest = float(request.form.get("interest", 5.0))
        except ValueError:
            urgency, fear, interest = 5.0, 5.0, 5.0

        if task_title:
            # 2. CALCULATE SCORE (Using the Python TMT Formula)
            # This ensures the backend math matches the frontend math
            impulsiveness = 1.5
            priority_score = calculate_tmt_score(urgency, fear, interest, impulsiveness)

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
            )
            db.session.add(task)
            db.session.commit()

            # 5. SAVE ANALYSIS (Log the data used for the score)
            analysis = models.TaskAnalysis(
                task_id=task.id,
                urgency_score=urgency,
                fear_score=fear,
                interest_score=interest,
                confidence=1.0,  # Validated by user
                model_version="MiniLM-L6-v2",
            )
            db.session.add(analysis)

            # 6. GET SUBTASKS (Call Gemini ONLY for breakdown)
            # We don't need its scores anymore, just the list
            ai_data = analyze_task(task_title)
            breakdown_steps = ai_data.get("breakdown", [])

            # --- DEBUGGING PRINTS ---
            print(f"DEBUG: Raw AI Response: {ai_data}")
            breakdown_steps = ai_data.get("breakdown", [])
            print(f"DEBUG: Steps found: {len(breakdown_steps)}")
            # ------------------------

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

    # For GET: fetch all tasks ordered by priority_score descending
    tasks = models.Task.query.order_by(models.Task.priority_score.desc()).all()
    return render_template("index.html", tasks=tasks)


@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json()
    text = data.get("title", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Get AI prediction using Local Vector Model
    metrics = predict_task_metrics(text)
    return jsonify(metrics)


if __name__ == "__main__":
    app.run(debug=True)
