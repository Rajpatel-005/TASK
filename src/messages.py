from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth import get_current_user
from src.db import create_message, get_chat_history, get_mongo_db, mark_message_as_read
from src.db.mongo import serialize_message

router = APIRouter(prefix="/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    receiver_id: int
    message: str = Field(..., min_length=1)



@router.post("")
def send_message(
    data: SendMessageRequest,
    mongo_db=Depends(get_mongo_db),
    user=Depends(get_current_user),
):

    msg = create_message(
        mongo_db,
        sender_id=int(user["sub"]),
        receiver_id=data.receiver_id,
        message=data.message,

    )
    return {"message": "Message sent successfully", "data": serialize_message(msg)}




@router.get("/{other_user_id}")
def get_messages(
    other_user_id: int,
    mongo_db=Depends(get_mongo_db),
    user=Depends(get_current_user),
):

    msgs = get_chat_history(
        mongo_db,
        user_id=int(user["sub"]),
        other_user_id=other_user_id,
    )

    return {"messages": msgs}


@router.patch("/{message_id}/read")
def read_message(
    message_id: str,
    mongo_db=Depends(get_mongo_db),
    user=Depends(get_current_user),
):

    msg = mark_message_as_read(
        mongo_db,
        message_id=message_id,
        reader_id=int(user["sub"]),
    )

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message marked as read", "data": msg}
