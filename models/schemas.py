from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ActionItemBase(BaseModel):
    text: str
    assignee: Optional[str] = None

class ActionItemCreate(ActionItemBase):
    pass

class ActionItem(ActionItemBase):
    id: int
    meeting_id: int
    status: str = "pending"

    class Config:
        from_attributes = True

class MeetingCreate(BaseModel):
    transcript: str

class Meeting(BaseModel):
    id: int
    title: str
    transcript: str
    created_at: datetime
    action_items: List[ActionItem] = []

    class Config:
        from_attributes = True

class EmailDraft(BaseModel):
    subject: str
    body: str

class ProcessResponse(BaseModel):
    meeting: Meeting
    action_items: List[ActionItem]
    email_draft: EmailDraft