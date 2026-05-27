import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.auth import verify_api_key
from app.db.session import get_db
from app.db.models import Feedback

router = APIRouter()


class FeedbackRequest(BaseModel):
    query_id: str
    track_id: str
    is_correct: bool
    clicked_position: Optional[int] = None


@router.post("")
async def post_feedback(req: FeedbackRequest, _: str = Depends(verify_api_key), db=Depends(get_db)):
    record = Feedback(id=str(uuid.uuid4()), query_id=req.query_id, track_id=req.track_id,
                      is_correct=req.is_correct, clicked_position=req.clicked_position)
    db.add(record)
    await db.commit()
    return {"status": "ok"}
