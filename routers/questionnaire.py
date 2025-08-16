from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from auth.jwt import get_current_user
from database import get_db
from models.questionnaire import UserQuestionnaire
from schema.questionnaire import QuestionnaireCreate, QuestionnaireResponse, QuestionnaireUpdate
from typing import Optional

quest_router = APIRouter(prefix="/questionnaire", tags=["Questionnaire"])

@quest_router.post("/", response_model=QuestionnaireResponse)
def upsert_questionnaire(
    data: QuestionnaireCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["user_id"]
    payload = data.model_dump(exclude_unset=True)  # only provided fields

    existing = (
        db.query(UserQuestionnaire)
        .filter(UserQuestionnaire.user_id == user_id)
        .first()
    )

    try:
        if existing:
            # update existing
            for field, value in payload.items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # create new
            row = UserQuestionnaire(user_id=user_id, **payload)
            db.add(row)
            db.commit()
            db.refresh(row)
            return row
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upsert failed: {e}")


@quest_router.get("/", response_model=Optional[QuestionnaireResponse])
def get_user_questionnaire(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's questionnaire"""
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    # Return None if no questionnaire exists (will be null in JSON response)
    return questionnaire

@quest_router.put("/", response_model=QuestionnaireResponse)
def update_questionnaire(
    data: QuestionnaireUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user questionnaire"""
    # Find existing questionnaire
    existing = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found. Use POST to create."
        )

    # Update fields that were provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    
    try:
        db.commit()
        db.refresh(existing)
        return existing
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update questionnaire: {str(e)}"
        )