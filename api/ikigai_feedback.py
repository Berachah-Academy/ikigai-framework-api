from fastapi import FastAPI, HTTPException
from api.models import *
from api.firebase import save_to_firebase
from api.gemini_feedback import generate_feedback_gemini
from api.ikigai_scores_and_questions import calculate_ikigai_scores

# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title="Ikigai Feedback API", version="1.0")

# ---------------------------
# API Endpoint
# ---------------------------
@app.post("/ikigai", response_model=IkigaiResponse)
def ikigai_feedback(req: IkigaiRequest):
    if not req.responses:
        raise HTTPException(status_code=400, detail="No responses provided")

    # Extract username correctly
    username = req.user.username

    ikigai_scores, ikigai_score = calculate_ikigai_scores(req.responses)

    # Gemini returns structured JSON
    feedback_json = generate_feedback_gemini(
        username,
        ikigai_scores,
        ikigai_score,
        req.responses
    )

    save_to_firebase(
        user=req.user,
        test_id=req.testId,
        finish_time=req.finishTime,
        responses=req.responses,
        ikigai_scores=ikigai_scores,
        ikigai_score=float(ikigai_score),
        feedback=feedback_json
    )


    return IkigaiResponse(
        ikigai_scores=ElementScores(**ikigai_scores),
        ikigai_alignment_score=float(ikigai_score),
        feedback=feedback_json
    )