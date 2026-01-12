from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict
from google import genai

client = genai.Client()

class IkigaiRequest(BaseModel):
    responses: Dict[str, str]

class ElementScores(BaseModel):
    LOVE: float
    SKILL: float
    WORLD: float
    PAID: float

class IkigaiResponse(BaseModel):
    element_scores: ElementScores
    ikigai_alignment_score: float
    feedback: str

OPTION_SCORE_MAP = {"A":1, "B":2, "C":3, "D":4, "E":5}
ELEMENT_QUESTIONS = {
    "LOVE": ["L1","L2","L3","L4","L5"],
    "SKILL": ["S1","S2","S3","S4","S5"],
    "WORLD": ["W1","W2","W3","W4","W5"],
    "PAID": ["P1","P2","P3","P4","P5"]
}
IKIGAI_WEIGHTS = {"LOVE":0.3, "SKILL":0.3, "WORLD":0.2, "PAID":0.2}

def calculate_element_score(responses, questions):
    total = 0
    for q in questions:
        if q not in responses:
            raise HTTPException(status_code=400, detail=f"Missing {q}")
        total += OPTION_SCORE_MAP[responses[q]]
    return round((total / 25) * 100, 2)

def calculate_scores(responses):
    element_scores = {
        el: calculate_element_score(responses, qs)
        for el, qs in ELEMENT_QUESTIONS.items()
    }
    ikigai_score = round(
        sum(element_scores[e] * IKIGAI_WEIGHTS[e] for e in element_scores), 2
    )
    return element_scores, ikigai_score

def generate_feedback(element_scores, ikigai_score):
    prompt = f"""
You are a career guidance expert.
Scores:
Love: {element_scores['LOVE']}
Skill: {element_scores['SKILL']}
World: {element_scores['WORLD']}
Paid: {element_scores['PAID']}
Overall: {ikigai_score}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )
    return response.text
