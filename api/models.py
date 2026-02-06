from typing import Dict
from pydantic import BaseModel

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
    testId: str | None = None
    finishTime: str | None = None

class ElementScores(BaseModel):
    love: float
    skill: float
    world: float
    paid: float

# ---------------- Feedback Models ----------------

class WeeklyPlan(BaseModel):
    week1: str
    week2: str
    week3: str
    week4: str

class ElementFeedback(BaseModel):
    summary: str
    feedback: str
    todo: str

class OverallFeedback(BaseModel):
    feedback: str
    plan: WeeklyPlan

class Feedback(BaseModel):
    love: ElementFeedback
    skill: ElementFeedback
    world: ElementFeedback
    paid: ElementFeedback
    overall: OverallFeedback

# ---------------- Final Response ----------------

class IkigaiResponse(BaseModel):
    ikigai_scores: ElementScores
    ikigai_alignment_score: float
    feedback: Feedback
