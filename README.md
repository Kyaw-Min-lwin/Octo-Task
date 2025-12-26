# Octo Task 🐙

An intelligent, ADHD-friendly task manager that uses Generative AI to break down overwhelming tasks and manage executive function.

## 🧠 The Philosophy
Standard to-do lists fail because they don't account for **Cognitive Load** or **Emotional Paralysis**. Octo Task uses the **INCUP** method (Interest, Novelty, Challenge, Urgency, Passion) to score tasks and automatically breaks complex projects into micro-steps to reduce friction.

## 🛠 Tech Stack
- **Backend:** Python (Flask), SQLAlchemy
- **Database:** PostgreSQL
- **AI/ML:** Google Gemini 2.5 Flash (via API)
- **Frontend:** HTML/CSS (Jinja2 Templates)

## ✨ Features
- **AI Analysis:** Automatically calculates Urgency, Fear, and Interest scores for every task.
- **Smart Breakdown:** Generates actionable subtasks for vague inputs (e.g., "Study for exam" -> "Open textbook", "Read Chapter 1", etc.).
- **Visual Sorting:** Prioritizes tasks based on a weighted algorithm tailored for neurodivergent brains.

## 🚀 Setup
1. Clone the repo.
2. Create `.env` with `DATABASE_URL` and `API_KEY`.
3. Run `flask db upgrade` to initialize PostgreSQL.
4. Run `python app.py`.