import os
import json
from fastapi import HTTPException

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
# Question & Answer mapper
# ---------------------------
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