from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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
    LOVE: float
    SKILL: float
    WORLD: float
    PAID: float

class IkigaiResponse(BaseModel):
    ikigai_scores: ElementScores
    ikigai_alignment_score: float
    feedback: str

# ---------------------------
# Ikigai scoring config
# ---------------------------
OPTION_SCORE_MAP = {"A":1, "B":2, "C":3, "D":4}
ELEMENT_QUESTIONS = {
    "LOVE": ["L1","L2","L3","L4","L5"],
    "SKILL": ["S1","S2","S3","S4","S5"],
    "WORLD": ["W1","W2","W3","W4","W5"],
    "PAID": ["P1","P2","P3","P4","P5"]
}
IKIGAI_WEIGHTS = {"LOVE":0.3, "SKILL":0.3, "WORLD":0.2, "PAID":0.2}

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
def generate_feedback_gemini(username, ikigai_scores, ikigai_score):
    prompt = f"""
You are an experienced career guidance counselor speaking directly to a student named {username}.

Based on the following Ikigai assessment scores, write a clear, friendly, and encouraging explanation in simple language.
Do not use headings, bullet points, numbering, emojis, symbols, or any text formatting.
Write only in plain paragraphs.

Ikigai Scores:
Love: {ikigai_scores['LOVE']}
Skill: {ikigai_scores['SKILL']}
World Need: {ikigai_scores['WORLD']}
Paid: {ikigai_scores['PAID']}
Overall Alignment: {ikigai_score}

Your response should naturally address {username} by name at least once and cover:
- What these scores suggest about {username}
- Strongest areas
- Areas that could improve with learning or experience
- Two or three suitable career directions, explained briefly

Keep the tone supportive, motivating, and easy for a student to understand.
Avoid generic advice and avoid repeating the score numbers.
Return only the feedback text.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

# ---------------------------
# API Endpoint
# ---------------------------
@app.post("/ikigai", response_model=IkigaiResponse)
def ikigai_feedback(req: IkigaiRequest):
    if not req.responses:
        raise HTTPException(status_code=400, detail="No responses provided")

    user = req.user
    ikigai_scores, ikigai_score = calculate_ikigai_scores(req.responses)

    feedback = generate_feedback_gemini(
        username=user.username,
        ikigai_scores=ikigai_scores,
        ikigai_score=ikigai_score
    )

    return IkigaiResponse(
        ikigai_scores=ElementScores(**ikigai_scores),
        ikigai_alignment_score=ikigai_score,
        feedback=feedback
    )
