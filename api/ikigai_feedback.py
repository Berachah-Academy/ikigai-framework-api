from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from datetime import datetime
from typing import Dict
from google import genai
client = genai.Client()

# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title="Ikigai Feedback API", version="1.0")

# ---------------------------
# Request / Response Models
# ---------------------------
class UserInfo(BaseModel):
    username: str
    email: str | None = None
    phone: str | None = None

class IkigaiRequest(BaseModel):
    user: UserInfo
    responses: Dict[str, str]

class ElementScores(BaseModel):
    love: float
    skill: float
    world: float
    paid: float

class IkigaiResponse(BaseModel):
    ikigai_scores: ElementScores
    ikigai_alignment_score: float
    feedback: Dict[str, str]

# ---------------------------
# Firebase Realtime DB
# ---------------------------

FIREBASE_DB_URL = "https://berachah-academy-default-rtdb.firebaseio.com"
IKIGAI_NODE = "ikigai-assessment"


def save_to_firebase(user: UserInfo, responses, ikigai_scores, ikigai_score, feedback):
    """
    Saves assessment to Firebase.
    Uses email (preferred) or username as user key.
    Each submission is appended with timestamp.
    """

    # Use email if present, else username (firebase-safe key)
    user_key = (user.email or user.username).replace(".", "_")

    timestamp = datetime.utcnow().isoformat()

    payload = {
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "submitted_at": timestamp,
        "responses": responses,
        "ikigai_scores": ikigai_scores,
        "ikigai_alignment_score": ikigai_score,
        "feedback": feedback
    }

    # POST will append under the user node
    url = f"{FIREBASE_DB_URL}/{IKIGAI_NODE}/{user_key}.json"

    r = requests.post(url, json=payload)

    if not r.ok:
        raise HTTPException(status_code=500, detail="Failed to save data to Firebase")


# ---------------------------
# Ikigai scoring config
# ---------------------------
OPTION_SCORE_MAP = {"A":1, "B":2, "C":3, "D":4}
ELEMENT_QUESTIONS = {
    "love": ["L1","L2","L3","L4","L5"],
    "skill": ["S1","S2","S3","S4","S5"],
    "world": ["W1","W2","W3","W4","W5"],
    "paid": ["P1","P2","P3","P4","P5"]
}
IKIGAI_WEIGHTS = {"love":0.3, "skill":0.3, "world":0.2, "paid":0.2}

# ---------------------------
# Scoring functions
# ---------------------------
def calculate_element_score(responses, questions):
    total = 0
    for q in questions:
        if q not in responses:
            raise HTTPException(status_code=400, detail=f"Missing response {q}")
        option = responses[q]
        if option not in OPTION_SCORE_MAP:
            raise HTTPException(status_code=400, detail=f"Invalid option {q}: {option}")
        total += OPTION_SCORE_MAP[option]
    return round((total/20)*100, 2)

def calculate_ikigai_scores(responses):
    ikigai_scores = {el: calculate_element_score(responses, qs)
                      for el, qs in ELEMENT_QUESTIONS.items()}
    ikigai_score = round(
        sum(ikigai_scores[el]*IKIGAI_WEIGHTS[el] for el in ikigai_scores), 2
    )
    return ikigai_scores, ikigai_score

# ---------------------------
# Gemini feedback generator
# ---------------------------
def parse_feedback(feedback_text):
    """
    Convert Gemini output into a dictionary per element.
    Expects each line in format:
    ELEMENT: advice
    """
    feedback_dict = {}
    lines = feedback_text.splitlines()
    
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            feedback_dict[key.strip().upper()] = value.strip()
    return feedback_dict

def generate_feedback_gemini(username, ikigai_scores, ikigai_score):
    prompt = f"""
You are an experienced career guidance counselor speaking directly to a student named {username}.

Provide a detail clear, and student-friendly piece of advice for each of the following Ikigai elements and score by the user:
1. Love - score {ikigai_scores["love"]}
2. Skill - score {ikigai_scores["skill"]}
3. World Need - score {ikigai_scores["world"]}
4. Paid - score {ikigai_scores["paid"]}
overall - {ikigai_score}

Then provide overall feedback based on the alignment score.

Return the feedback **as a single string**, with each element's advice **on a separate line**, in this exact format:

LOVE: <advice for love>
SKILL: <advice for skill>
WORLD: <advice for world>
PAID: <advice for paid>
OVERALL: <overall advice>

Do not use headings, bullet points, numbering, emojis, symbols, or extra text. Keep it concise, friendly, and motivational.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

# ---------------------------
# API Endpoint
# ---------------------------
@app.post("/ikigai", response_model=IkigaiResponse)
def ikigai_feedback(req: IkigaiRequest):
    if not req.responses:
        raise HTTPException(status_code=400, detail="No responses provided")

    username = req.user.username

    ikigai_scores, ikigai_score = calculate_ikigai_scores(req.responses)

    feedback_text = generate_feedback_gemini(username, ikigai_scores, ikigai_score)
    feedback_dict = parse_feedback(feedback_text)

    # Save to Firebase (append if user exists)
    save_to_firebase(
        user=req.user,
        responses=req.responses,
        ikigai_scores=ikigai_scores,
        ikigai_score=ikigai_score,
        feedback=feedback_dict
    )

    return IkigaiResponse(
        ikigai_scores=ElementScores(**ikigai_scores),
        ikigai_alignment_score=ikigai_score,
        feedback=feedback_dict
    )
