from services.nlp_services import nlp_engine

# --- TUNING CONFIGURATION (The "Physics" Constants) ---

# SCORE BOUNDARIES: Keep inputs within the 1-10 scale.
SCORE_MIN = 1
SCORE_MAX = 10

# EXPECTANCY BUFFER: The "Hope" Constant.
# We calculate Expectancy = (BUFFER - Fear).
# If Buffer is 10 and Fear is 10, Expectancy is 0 (Paralysis).
# We use 12 so that even at Max Fear, you still have a score of 2.
EXPECTANCY_BUFFER = 12

# FEAR ACCELERATOR: The "Panic Monster" Effect.
# ADHD brains often convert Fear into Urgency.
# 0.3 means 30% of your Fear score is added to your Urgency score.
FEAR_ACCELERATOR = 0.3

# MINIMUM DELAY: The "Now" Buffer.
# Prevents division by zero when Urgency is 10/10 (Deadline is Now).
MIN_DELAY = 0.1

# DEFAULT IMPULSIVENESS: The "Time Blindness" Factor.
# This makes the denominator grow faster.
# Standard people might be 0.5 - 1.0. ADHD is usually 1.5 - 2.0.
DEFAULT_IMPULSIVENESS = 1.5

# MAX UTILITY CAP: Just to keep the UI clean.
# Prevents a score of 4000 if the math gets weird.
UTILITY_CAP = 100


def calculate_tmt_score(urgency, fear, interest, impulsiveness=None):
    """
    ADHD-Adjusted Temporal Motivation Theory
    Utility = (Expectancy * Value) / (1 + Impulsiveness * Delay)
    """
    if impulsiveness is None:
        impulsiveness = DEFAULT_IMPULSIVENESS

    # 1. Clamp Inputs (Sanity Check)
    urgency = min(SCORE_MAX, max(SCORE_MIN, urgency))
    fear = min(SCORE_MAX, max(SCORE_MIN, fear))
    interest = min(SCORE_MAX, max(SCORE_MIN, interest))

    # 2. EXPECTANCY (Confidence)
    # "How likely am I to succeed?"
    # High Fear kills Expectancy.
    E = max(1, EXPECTANCY_BUFFER - fear)

    # 3. VALUE (Dopamine)
    # "How much do I want this?"
    V = interest

    # 4. EFFECTIVE URGENCY (The Panic Adjustment)
    # If you are terrified (Fear 10), it feels more Urgent even if the deadline is far.
    effective_urgency = min(SCORE_MAX, urgency + (fear * FEAR_ACCELERATOR))

    # 5. DELAY (Time)
    # "How long do I have to wait?"
    # High Urgency = Low Delay.
    D = max(MIN_DELAY, SCORE_MAX - effective_urgency)

    # 6. THE EQUATION
    denominator = 1 + (impulsiveness * D)
    utility = (E * V) / denominator

    # 7. Final Polish
    utility = min(UTILITY_CAP, utility)

    return round(utility, 2)


def get_user_impulsiveness(user_id=None):
    # Placeholder: In the future, fetch this from the User table
    return DEFAULT_IMPULSIVENESS


def predict_task_metrics(task_text, user_id=None):
    # 1. AI Analysis
    metrics = nlp_engine.analyze_task(task_text)

    # 2. Physics Calculation
    impulsiveness = get_user_impulsiveness(user_id)

    final_score = calculate_tmt_score(
        metrics["urgency"], metrics["fear"], metrics["interest"], impulsiveness
    )
    priority_pressure = metrics["urgency"] * 2 + metrics["fear"]
    final_priority = priority_pressure * 0.6 + final_score * 0.4

    metrics["motivation_score"] = round(final_score, 2)
    metrics["priority_score"] = round(final_priority, 2)

    return metrics
