# Changelog

All notable changes to the "Octo Task" project will be documented in this file.

## [Unreleased]
- **Feature:** "Start Task" session timer.
- **Feature:** User Authentication (Login/Register).
- **Feature:** Distraction detection logic.

## [0.2.0] - 2025-12-20
### Added
- **AI Integration:** Added `ai_service.py` using Google Gemini 1.5 Flash.
- **NLP Analysis:** Tasks are now automatically analyzed for Urgency, Fear, and Interest scores.
- **Auto-Breakdown:** Tasks are automatically split into subtasks by the AI.
- **Frontend:** Updated `index.html` to display priority scores and nested subtasks visually.

### Changed
- **Scoring Logic:** Replaced random number generation with AI-driven scoring.
- **Database:** Updated `app.py` to save `TaskAnalysis` and `Subtask` objects linked to the main Task.

## [0.1.0] - 2025-12-20
### Added
- **Project Setup:** Initialized Flask, Virtual Environment, and PostgreSQL connection.
- **Database:** Created `flask_db` and configured `flask_user`.
- **Models:** Defined SQLAlchemy models for `User`, `Task`, `Subtask`, `TaskAnalysis`, `TaskScore`, `TaskSession`.
- **Migrations:** Configured Flask-Migrate and ran initial migration.
- **Basic UI:** Created basic `index.html` to list tasks.