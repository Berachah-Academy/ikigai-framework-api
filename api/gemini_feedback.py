import os
import json
from google import genai
from fastapi import HTTPException
from api.ikigai_scores_and_questions import build_user_qna

# ---------------------------
# Gemini API Config
# ---------------------------
GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]

# ---------------------------
# Gemini feedback generator
# ---------------------------
def generate_feedback_gemini(username, ikigai_scores, ikigai_score, responses):
    user_qna = build_user_qna(responses)
    prompt = f"""
You are an experienced career guidance counselor speaking directly to a student named {username}.

Below are the student's exact answers:

{user_qna}

Ikigai scores:
Love: {ikigai_scores["love"]}
Skill: {ikigai_scores["skill"]}
World Need: {ikigai_scores["world"]}
Paid: {ikigai_scores["paid"]}
Overall: {ikigai_score}

Use BOTH the student's answers AND the scores.

For EACH Ikigai element:
- Explain what their answers + score mean
- Give clear personalized feedback
- Give practical improvement actions
- Provide specific "what to do next"

For OVERALL:
- Give career readiness feedback
- List 2-3 priority gaps
- Provide a detailed 30 day action plan broken into weekly steps

For each element, also provide a very short micro summary (maximum 5 words) describing the student's current status (for example: "Exploring interests", "Needs consistent practice", "Unclear career direction").

Return ONLY valid JSON in this exact structure:

{{
  "love": {{
    "summary": "",
    "feedback": "",
    "todo": ""
  }},
  "skill": {{
    "summary": "",
    "feedback": "",
    "todo": ""
  }},
  "world": {{
    "summary": "",
    "feedback": "",
    "todo": ""
  }},
  "paid": {{
    "summary": "",
    "feedback": "",
    "todo": ""
  }},
  "overall": {{
    "feedback": "",
    "plan": {{
      "week1": "",
      "week2": "",
      "week3": "",
      "week4": ""
    }}
  }}
}}

Do NOT include markdown, headings, bullets, emojis, or extra text. Only pure JSON.
"""
    last_error = None

    for idx, api_key in enumerate(GEMINI_API_KEYS):
        if not api_key:
            continue

        try:
            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            raw_text = response.text.strip()

            feedback_json = json.loads(raw_text)
            return feedback_json, idx + 1

        except json.JSONDecodeError:
            last_error = "Invalid JSON"
            continue

        except Exception as e:
            last_error = str(e)
            continue

    raise HTTPException(
        status_code=500,
        detail=f"All Gemini API keys exhausted. Last error: {last_error}"
    )
