# ---------------------------
# Logging
# ---------------------------
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

from api.models import *
from api.firebase import save_to_firebase
from api.gemini_feedback import generate_feedback_gemini
from api.ikigai_scores_and_questions import calculate_ikigai_scores

from fastapi import FastAPI, HTTPException

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
    
    logger.info("Ikigai request received")
    logger.info(f"User: {req.user.username}")
    logger.info(f"Test ID: {req.testId}")
    logger.info(f"Finish Time: {req.finishTime}")
    logger.info(f"Total Responses: {len(req.responses)}")

    ikigai_scores, ikigai_score = calculate_ikigai_scores(req.responses)

    logger.info(f"Ikigai Scores: {ikigai_scores}")
    logger.info(f"Overall Ikigai Score: {ikigai_score}")

    # Gemini returns structured JSON
    feedback_json, gemini_key_id = generate_feedback_gemini(
        req.user.username,
        ikigai_scores,
        ikigai_score,
        req.responses
    )

    logger.info(f"Gemini feedback generated successfully using key: {gemini_key_id}")

    save_to_firebase(
        user=req.user,
        test_id=req.testId,
        finish_time=req.finishTime,
        responses=req.responses,
        ikigai_scores=ikigai_scores,
        ikigai_score=float(ikigai_score),
        feedback=feedback_json
    )

    logger.info("Data saved to Firebase")

    return IkigaiResponse(
        ikigai_scores=ElementScores(**ikigai_scores),
        ikigai_alignment_score=float(ikigai_score),
        feedback=feedback_json
    )