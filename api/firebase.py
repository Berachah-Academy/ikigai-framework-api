import requests

FIREBASE_DB_URL = "https://berachah-academy-default-rtdb.firebaseio.com"
IKIGAI_NODE = "ikigai/assessment-result"

# ---------------------------
# Save user data in firebase
# ---------------------------
def save_to_firebase(user, test_id, finish_time, responses, ikigai_scores, ikigai_score, feedback):

    if not test_id:
        print("Missing test_id, skipping Firebase save")
        return

    payload = {
        "user": {
            "username": user.username,
            "email": user.email,
            "phone": user.phone
        },
        "completedAt": finish_time,
        "responses": responses,
        "ikigai_scores": ikigai_scores,
        "ikigai_alignment_score": ikigai_score,
        "feedback": feedback
    }

    base_url = f"{FIREBASE_DB_URL}/{IKIGAI_NODE}/{test_id}.json"

    try:
        r = requests.put(base_url, json=payload, timeout=8)

        if not r.ok:
            print("Firebase write failed:", r.status_code, r.text)

    except Exception as e:
        print("Firebase exception:", str(e))
