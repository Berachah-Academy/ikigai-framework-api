from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from google import genai
client = genai.Client()

import re
import requests
from datetime import datetime

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(BASE_DIR, "ikigai_questions.json")

with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    QUESTIONS_DATA = json.load(f)["questions"]

# Group questions by element
QUESTIONS_BY_ELEMENT = {}
for q in QUESTIONS_DATA:
    QUESTIONS_BY_ELEMENT.setdefault(q["element"].lower(), []).append(q)

def build_user_qna(responses):
    """
    Returns formatted string of:
    Element
    Question
    Selected answer
    """

    result = []

    for element, questions in QUESTIONS_BY_ELEMENT.items():
        result.append(f"{element.upper()}:")

        for idx, q in enumerate(questions, start=1):
            key = f"{element[0].upper()}{idx}"  # L1, S1, W1, P1

            if key not in responses:
                continue

            selected_score = OPTION_SCORE_MAP.get(responses[key])

            chosen_text = "Unknown"

            for opt in q["options"]:
                if opt["score"] == selected_score:
                    chosen_text = opt["text"]
                    break

            result.append(f"- Q: {q['question']}")
            result.append(f"- A: {chosen_text}")

        result.append("")

    return "\n".join(result)


FIREBASE_DB_URL = "https://berachah-academy-default-rtdb.firebaseio.com"
IKIGAI_NODE = "ikigai-assessment"


def save_to_firebase(user, responses, ikigai_scores, ikigai_score, feedback):
    # Firebase-safe user key
    raw_key = user.email
    user_key = re.sub(r'[.$#[\]/@]', "_", raw_key)

    payload = {
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "submitted_at": datetime.utcnow().isoformat(),
        "responses": responses,
        "ikigai_scores": ikigai_scores,
        "ikigai_alignment_score": ikigai_score,
        "feedback": feedback
    }

    url = f"{FIREBASE_DB_URL}/{IKIGAI_NODE}/{user_key}.json"

    try:
        # POST = append
        r = requests.post(url, json=payload, timeout=6)

        # Log only — NEVER raise
        if not r.ok:
            print("Firebase write failed:", r.status_code, r.text)

    except Exception as e:
        # Never crash API because of Firebase
        print("Firebase exception:", str(e))

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
def generate_feedback_gemini(username, ikigai_scores, ikigai_score, responses):
    user_qna = build_user_qna(responses)
    prompt = f"""
You are an experienced career guidance counselor speaking directly to a student named {username}.

Below are the student's exact answers:

{user_qna}

Ikigai scores:
Love: {ikigai_scores["love"]}
Skill: {ikigai_scores["skill"]}
World Need: {ikigai_scores["world"]}
Paid: {ikigai_scores["paid"]}
Overall: {ikigai_score}

Use BOTH the student's answers AND the scores.

For EACH Ikigai element:
- Explain what their answers + score mean
- Give clear personalized feedback
- Give practical improvement actions
- Provide specific "what to do next"

For OVERALL:
- Give career readiness feedback
- List 2-3 priority gaps
- Provide a detailed 30 day action plan broken into weekly steps

Return ONLY valid JSON in this exact structure:

{
  "love": {
    "feedback": "",
    "todo": ""
  },
  "skill": {
    "feedback": "",
    "todo": ""
  },
  "world": {
    "feedback": "",
    "todo": ""
  },
  "paid": {
    "feedback": "",
    "todo": ""
  },
  "overall": {
    "feedback": "",
    "30_day_plan": ""
  }
}

Do NOT include markdown, headings, bullets, emojis, or extra text. Only pure JSON.
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        raw_text = response.text.strip()

        # Convert Gemini output into Python dict
        feedback_json = json.loads(raw_text)

        return feedback_json

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON returned from Gemini")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

# ---------------------------
# API Endpoint
# ---------------------------
@app.post("/ikigai", response_model=IkigaiResponse)
def ikigai_feedback(req: IkigaiRequest):
    if not req.responses:
        raise HTTPException(status_code=400, detail="No responses provided")

    username = req.user

    ikigai_scores, ikigai_score = calculate_ikigai_scores(req.responses)

    # Gemini now returns JSON directly
    feedback_json = generate_feedback_gemini(
        username,
        ikigai_scores,
        ikigai_score,
        req.responses
    )

    save_to_firebase(
        user=req.user,
        responses=req.responses,
        ikigai_scores=ikigai_scores,
        ikigai_score=ikigai_score,
        feedback=feedback_json
    )

    return IkigaiResponse(
        ikigai_scores=ElementScores(**ikigai_scores),
        ikigai_alignment_score=ikigai_score,
        feedback=feedback_json
    )