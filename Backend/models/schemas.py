from pydantic import BaseModel, Field, field_validator
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
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full plain-text email body with real line breaks")

class ProcessResponse(BaseModel):
    meeting: Meeting
    action_items: List[ActionItem]
    email_draft: EmailDraft

# Structured outputs the agents must return

class ExtractedActionItem(BaseModel):
    text: str = Field(description="What needs to be done, as a short imperative sentence")
    assignee: Optional[str] = Field(
        default=None,
        description="Name of the person responsible, or null if nobody was named"
    )

    @field_validator("assignee")
    @classmethod
    def blank_assignee_to_none(cls, value):
        if value is None or value.strip().lower() in {"", "null", "none", "unassigned", "n/a"}:
            return None
        return value.strip()

class ExtractionOutput(BaseModel):
    title: str = Field(description="Short 5-7 word title summarising the meeting topic")
    action_items: List[ExtractedActionItem] = Field(
        description="Every task someone agreed or was asked to do"
    )

class SummaryOutput(BaseModel):
    overview: str = Field(description="One sentence describing what the meeting was about")
    key_points: List[str] = Field(description="2-3 key discussion points")
    decisions: str = Field(description="One or two sentences about decisions made")
