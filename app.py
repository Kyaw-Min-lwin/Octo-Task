from flask import Flask, render_template, request, redirect, url_for
from extensions import db
from flask_migrate import Migrate
import models
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
import random
from ai_service import analyze_task

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        task_title = request.form.get("task_title")
        if task_title:
            ai_data = analyze_task(task_title)

            # Extract scores (default to 5 if something breaks)
            urgency = ai_data.get("urgency", 5)
            fear = ai_data.get("fear", 5)
            interest = ai_data.get("interest", 5)

            # Calculate Priority (ADHD Formula)
            priority_score = (urgency * 1.5) + (interest * 1.0) - (fear * 0.5)

            user = models.User.query.first()
            if not user:
                user = models.User(
                    email="default@example.com",
                    username="default",
                    password_hash="dummy",
                )
                db.session.add(user)
                db.session.commit()

            task = models.Task(
                user_id=user.id,
                title=task_title,
                priority_score=priority_score,
                status="pending",
            )
            db.session.add(task)
            db.session.commit()

            # Create TaskAnalysis
            analysis = models.TaskAnalysis(
                task_id=task.id,
                urgency_score=urgency,
                fear_score=fear,
                interest_score=interest,
                confidence=random.uniform(0.5, 1),
                model_version="gemini-2.5-flash",
            )
            db.session.add(analysis)

            breakdown_steps = ai_data.get("breakdown", [])

            for index, step_text in enumerate(breakdown_steps):
                subtask = models.Subtask(
                    task_id=task.id,
                    title=step_text,
                    order_index=index,
                    status="pending",
                    created_by="ai",
                )
                db.session.add(subtask)
            db.session.commit()

        return redirect(url_for("index"))

    # For GET: fetch all tasks ordered by priority_score descending
    tasks = models.Task.query.order_by(models.Task.priority_score.desc()).all()
    return render_template("index.html", tasks=tasks)


if __name__ == "__main__":
    app.run(debug=True)
