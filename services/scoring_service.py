from services.nlp_services import nlp_engine


def calculate_tmt_score(urgency, fear, interest, impulsiveness):
    """
    ADHD-Adjusted Temporal Motivation Theory
    """

    # Expectancy (confidence)
    E = max(1, 12 - fear)

    # Value (interest)
    V = interest


    # Fear slightly increases urgency (panic-start effect)
    effective_urgency = min(10, urgency + fear * 0.3)

    # Delay
    D = max(0.1, 10 - effective_urgency)

    # Impulsiveness penalty
    denominator = 1 + (impulsiveness * D)

    utility = (E * V) / denominator

    # Soft cap
    utility = min(100, utility)

    return round(utility, 2)


def get_user_impulsiveness(user_id=None):
    # Placeholder: In the future, fetch this from the User table
    # Standard ADHD range is often higher (1.5 - 2.0)
    return 1.5

def predict_task_metrics(task_text, user_id=None):
    # 1. AI Analysis
    metrics = nlp_engine.analyze_task(task_text)
    
    # 2. Physics Calculation
    impulsiveness = get_user_impulsiveness(user_id)
    
    final_score = calculate_tmt_score(
        metrics['urgency'], 
        metrics['fear'], 
        metrics['interest'],
        impulsiveness
    )
    
    metrics['priority_score'] = final_score
    return metrics