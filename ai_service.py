import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

genai.configure(api_key=os.getenv("API_KEY"))

def analyze_task(task_description):
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # We force the model to return JSON so your code doesn't break
    prompt = f"""
    Analyze this task for an ADHD brain: "{task_description}"
    
    Return a JSON object with these exact keys:
    - "urgency": integer 1-10 (10 is immediate deadline)
    - "fear": integer 1-10 (how scary/overwhelming is this task?)
    - "interest": integer 1-10 (how dopamine-inducing is this?)
    - "breakdown": a list of 3-5 sub-steps to make it less scary.
    
    Do not use markdown. Just raw JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean up response if it adds markdown ```json blocks
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"AI Error: {e}")
        # Fallback if AI fails
        return {"urgency": 5, "fear": 5, "interest": 5, "breakdown": []}