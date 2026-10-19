from sqlalchemy.orm import Session
from db.database import MeetingModel, ActionItemModel
from models.schemas import MeetingCreate, ActionItemCreate
from datetime import datetime

def create_meeting(db: Session, title: str, transcript: str) -> MeetingModel:
    meeting = MeetingModel(
        title=title,
        transcript=transcript,
        created_at=datetime.utcnow()
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting

def get_all_meetings(db: Session) -> list[MeetingModel]:
    return db.query(MeetingModel).order_by(MeetingModel.created_at.desc()).all()

def get_meeting_by_id(db: Session, meeting_id: int) -> MeetingModel:
    return db.query(MeetingModel).filter(MeetingModel.id == meeting_id).first()

def create_action_items(db: Session, meeting_id: int, items: list[dict]) -> list[ActionItemModel]:
    action_items = []
    for item in items:
        action_item = ActionItemModel(
            meeting_id=meeting_id,
            text=item.get("text", ""),
            assignee=item.get("assignee", None),
            status="pending"
        )
        db.add(action_item)
        action_items.append(action_item)
    db.commit()
    for item in action_items:
        db.refresh(item)
    return action_items

def get_action_items_by_meeting(db: Session, meeting_id: int) -> list[ActionItemModel]:
    return db.query(ActionItemModel).filter(
        ActionItemModel.meeting_id == meeting_id
    ).all()

def update_action_item(db: Session, item_id: int, text: str = None, status: str = None) -> ActionItemModel:
    item = db.query(ActionItemModel).filter(ActionItemModel.id == item_id).first()
    if not item:
        return None
    if text is not None:
        item.text = text
    if status is not None:
        item.status = status
    db.commit()
    db.refresh(item)
    return item

def delete_meeting(db: Session, meeting_id: int):
    db.query(ActionItemModel).filter(
        ActionItemModel.meeting_id == meeting_id
    ).delete()
    db.query(MeetingModel).filter(
        MeetingModel.id == meeting_id
    ).delete()
    db.commit()

def create_meeting(db: Session, title: str, transcript: str, summary: str = None) -> MeetingModel:
    meeting = MeetingModel(
        title=title,
        transcript=transcript,
        summary=summary,
        created_at=datetime.utcnow()
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting