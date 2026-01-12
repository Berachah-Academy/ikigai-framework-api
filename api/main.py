from fastapi import FastAPI
from api.ikigai_feedback import ikigai_feedback

app = FastAPI(title="Ikigai API")

@app.post("/ikigai")
def run_ikigai(req: dict):
    return ikigai_feedback(req)