from fastapi import FastAPI, Body
from pydantic import BaseModel

app = FastAPI(
    title="AI Services Layer - Claims Processing Engine",
    description="Live microservice evaluating incoming claims for Denial Probability.",
    version="1.0.0"
)

# Response model Boomi expects
class PredictionResponse(BaseModel):
    claimId: str
    denialScore: float
    status: str

# Recursive helper to find keys anywhere in nested Boomi JSON
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
        # --- Read values from the Boomi payload ---
        claim_id = str(find_key(payload, "ClaimID", "CLM-DEMO-999"))

        raw_amount = find_key(payload, "BilledAmount", 0.0)
        try:
            billed_amount = float(raw_amount)
        except (ValueError, TypeError):
            billed_amount = 0.0

        # We'll use PriorAuth as a demo risk trigger
        prior_auth = str(find_key(payload, "PriorAuth", "")).strip().upper()

        # ---------------------------------------------------
        # DEMO-FRIENDLY RULES:
        # 1) Force REJECTED if PriorAuth starts with "REJECT"
        # 2) Force APPROVED if PriorAuth starts with "APPROVE"
        # 3) Otherwise use amount-based scoring
        # ---------------------------------------------------

        # Hard-coded demo outcomes
        if prior_auth.startswith("REJECT"):
            return {
                "claimId": claim_id,
                "denialScore": 0.91,
                "status": "Rejected"
            }

        if prior_auth.startswith("APPROVE"):
            return {
                "claimId": claim_id,
                "denialScore": 0.18,
                "status": "Approved"
            }

        # Normal scoring logic if no explicit demo trigger is provided
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

    except Exception as e:
        # Safe fallback for demo stability
        return {
            "claimId": "CLM-RESCUE",
            "denialScore": 0.12,
            "status": "Approved"
        }
