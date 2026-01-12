from fastapi.middleware.cors import CORSMiddleware
from api.ikigai_feedback import app as ikigai_app

# This file only exposes the FastAPI app
# Vercel / Uvicorn will look for `app`

app = ikigai_app

# CORS configuration
origins = [
    "http://localhost:8080",  # your frontend during development
    # add your production frontend URL here, e.g.:
    # "https://your-frontend-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # allow specific origins
    allow_credentials=True,
    allow_methods=["*"],         # allow all HTTP methods
    allow_headers=["*"],         # allow all headers
)