from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import random

app = FastAPI(
    title="AI Services Layer - Claims Processing Engine",
    description="Live microservice evaluating incoming claims for Denial Probability.",
    version="1.0.0"
)

# Canonical Data Model Schema matching Boomi's target output
class ClaimData(BaseModel):
    claimId: str
    patientId: str
    patientAge: int
    diagnosisCode: str
    procedureCode: str
    claimAmount: float
    providerId: str

class PredictionResponse(BaseModel):
    claimId: str
    denial_probability: float
    threshold_exceeded: bool
    status: str
    engine: str

@app.post("/predict/denial-probability", response_model=PredictionResponse)
async def predict_denial(claim: ClaimData):
    try:
        # Placeholder logic simulating the XGBoost/Random Forest core
        base_risk = 0.20
        
        # Scenario 1: High claim amounts increase denial risk
        if claim.claimAmount > 5000:
            base_risk += 0.40
            
        # Scenario 2: Specific diagnosis prefixes (e.g., Endocrine 'E') add risk
        if claim.diagnosisCode.upper().startswith("E"):
            base_risk += 0.25
            
        # Generate a realistic final probability score bounded between 0 and 1
        final_probability = min(base_risk + random.uniform(-0.05, 0.1), 0.99)
        final_probability = max(final_probability, 0.01)
        
        # Architectural threshold rule (e.g., > 70% gets flagged for rejection)
        denial_threshold = 0.70
        is_denied = final_probability > denial_threshold
        
        return {
            "claimId": claim.claimId,
            "denial_probability": round(final_probability, 4),
            "threshold_exceeded": is_denied,
            "status": "Rejected" if is_denied else "Approved",
            "engine": "XGBoost-Simulation-v1"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference Engine Error: {str(e)}")