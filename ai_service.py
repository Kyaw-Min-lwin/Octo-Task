import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

genai.configure(api_key=os.getenv("API_KEY"))


def analyze_task(task_description):
    # Use the standard flash model (fast & cheap)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # NEW PROMPT: Focus ONLY on breakdown
    prompt = f"""
    You are an expert ADHD Coach. 
    The user is feeling overwhelmed by this task: "{task_description}"
    1. Break this task down into 3-5 concrete, actionable sub-goals (MVP first).
    2. Estimate the "Cognitive Load" (Difficulty) on a scale of 1-10.
       - 1 = Trivial (Buy milk)
       - 10 = Herculean (Write a thesis in 2 hours)
       RULES:
    1. Respect the user's intelligence. Do NOT include steps like "Open laptop", "Turn on screen", or "Type in search bar".
    2. Focus on "Cognitive Chunks" (logical units of work) rather than mechanical actions.
    3. The first step must be the "MVP" (Minimum Viable Progress) to get them started.
    Return ONLY a JSON object with these keys:
    - "breakdown": [list of strings]
    - "difficulty": integer (1-10)
    Example output format:
    {{
        "breakdown": ["Quickly skim the entire assignment prompt to understand the overall goal and key deliverables.", "Outline the high-level logic or main components required for the solution."],
        "difficulty": 3
    }}
    Do not use markdown. Just raw JSON.
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    except Exception as e:
        print(f"AI Breakdown Error: {e}")
        # Fallback: Return an empty list if AI fails, so the app doesn't crash
        return {"breakdown": []}
