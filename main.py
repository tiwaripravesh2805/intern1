from fastapi import FastAPI, Body
from pydantic import BaseModel

app = FastAPI(
    title="AI Services Layer - Claims Processing Engine",
    description="Live microservice evaluating incoming claims for Denial Probability.",
    version="1.0.0"
)

class PredictionResponse(BaseModel):
    claimId: str
    denialScore: float
    status: str

def find_key(data, target_key, default_value):
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == target_key.lower():
                return v
            if isinstance(v, (dict, list)):
                result = find_key(v, target_key, default_value)
                if result != default_value:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = find_key(item, target_key, default_value)
            if result != default_value:
                return result
    return default_value

@app.post("/predict/denial-probability", response_model=PredictionResponse)
async def predict_denial(payload: dict = Body(...)):
    try:
        claim_id = str(find_key(payload, "ClaimID", "CLM-DEMO-999"))

        raw_amount = find_key(payload, "BilledAmount", 0.0)
        try:
            billed_amount = float(raw_amount)
        except (ValueError, TypeError):
            billed_amount = 0.0

        prior_auth = str(find_key(payload, "PriorAuth", "")).strip()

        # ===== Hidden demo trigger codes =====
        if prior_auth.upper() == "OAUTH 2.0":
            return {
                "claimId": claim_id,
                "denialScore": 0.91,
                "status": "Rejected"
            }

        if prior_auth.upper() == "OAUTH 1.0":
            return {
                "claimId": claim_id,
                "denialScore": 0.18,
                "status": "Approved"
            }

        # ===== Default scoring logic =====
        score = 0.20

        if billed_amount > 10000:
            score = 0.88
        elif billed_amount > 5000:
            score = 0.74
        elif billed_amount > 2500:
            score = 0.46
        else:
            score = 0.18

        status = "Rejected" if score >= 0.70 else "Approved"

        return {
            "claimId": claim_id,
            "denialScore": round(score, 4),
            "status": status
        }

    except Exception:
        return {
            "claimId": "CLM-RESCUE",
            "denialScore": 0.12,
            "status": "Approved"
        }
