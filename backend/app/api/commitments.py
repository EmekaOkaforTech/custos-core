from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.commitment import Commitment

router = APIRouter(prefix="/api/commitments", tags=["commitments"])


class CommitmentAckRequest(BaseModel):
    acknowledged: bool


@router.post("/{commitment_id}/ack")
def acknowledge_commitment(
    commitment_id: str,
    request: CommitmentAckRequest,
    db: Session = Depends(get_db),
) -> dict:
    commitment = db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    commitment.acknowledged = request.acknowledged
    db.commit()
    return {
        "id": commitment.id,
        "acknowledged": commitment.acknowledged,
        "updated_at": commitment.updated_at,
    }
