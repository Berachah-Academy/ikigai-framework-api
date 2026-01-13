from fastapi.middleware.cors import CORSMiddleware
from api.ikigai_feedback import app as ikigai_app

app = ikigai_app

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # allow all origins
    allow_credentials=False, # MUST be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)
