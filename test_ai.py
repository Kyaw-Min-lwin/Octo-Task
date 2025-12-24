from services.scoring_service import predict_task_metrics

test_tasks = [
    # High urgency + fear
    "Finish my final year thesis dissertation",
    "Submit assignment due tonight",
    "Study for exam starting in 3 hours",
    # High urgency, low fear
    "Send quick email to confirm meeting today",
    "Upload document before 5pm",
    # High fear, low urgency
    "Do my taxes",
    "Call the bank about an issue",
    # High interest, low urgency
    "Play a good mobile game to pass time",
    "Work on personal side project",
    # Boring chores
    "Clean my room",
    "Do laundry",
    # Trivial errands
    "Buy milk",
    "Pick up toothpaste",
    # Panic triggers
    "Write essay due in 2 hours",
    "Finish report ASAP",
    "Create a coding web project which is a school assignment and it is due tonight",
]

print(f"{'TASK':<40} | {'URG':<5} | {'FEAR':<5} | {'INT':<5} | {'SCORE':<5}")
print("-" * 85)

for task in test_tasks:
    result = predict_task_metrics(task)
    print(
        f"{task:<40} | {result['urgency']:<5} | {result['fear']:<5} | {result['interest']:<5} | {result['priority_score']:<5}"
    )
