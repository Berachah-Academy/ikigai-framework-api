from fastapi import FastAPI
from api.ikigai_feedback import (
    IkigaiRequest,
    IkigaiResponse,
    ElementScores,
    calculate_scores,
    generate_feedback
)

app = FastAPI(title="Ikigai API")

@app.post("/ikigai", response_model=IkigaiResponse)
async def run_ikigai(req: IkigaiRequest):
    element_scores, ikigai_score = calculate_scores(req.responses)
    feedback = generate_feedback(element_scores, ikigai_score)

    return IkigaiResponse(
        element_scores=ElementScores(**element_scores),
        ikigai_alignment_score=ikigai_score,
        feedback=feedback
    )