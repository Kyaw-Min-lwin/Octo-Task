from services.scoring_service import predict_task_metrics

test_tasks = [
    "Finish my final year thesis dissertation",  # Should be Scary, Urgent
    "Play a good mobile game to pass time",  # Should be Interesting, Not Scary
    "Do my taxes",  # Should be Boring, Scary
    "Buy milk",
    "Write essay due in 1 hour",  # Should be Easy, Low Interest
]

print(f"{'TASK':<40} | {'URG':<5} | {'FEAR':<5} | {'INT':<5} | {'SCORE':<5}")
print("-" * 85)

for task in test_tasks:
    result = predict_task_metrics(task)
    print(
        f"{task:<40} | {result['urgency']:<5} | {result['fear']:<5} | {result['interest']:<5} | {result['priority_score']:<5}"
    )
