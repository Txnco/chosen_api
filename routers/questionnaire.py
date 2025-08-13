from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from auth.jwt import get_current_user
from database import get_db
from models.questionnaire import UserQuestionnaire
from schema.questionnaire import QuestionnaireCreate, QuestionnaireResponse, QuestionnaireUpdate
from typing import Optional

quest_router = APIRouter(prefix="/questionnaire", tags=["Questionnaire"])

@quest_router.post("/", response_model=QuestionnaireResponse)
def create_questionnaire(
    data: QuestionnaireCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create/Submit user questionnaire"""
    # Check if user already has a questionnaire
    existing = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Questionnaire already exists. Use PUT to update."
        )

    # Create new questionnaire
    questionnaire = UserQuestionnaire(
        user_id=current_user["user_id"],
        **data.model_dump()
    )
    
    try:
        db.add(questionnaire)
        db.commit()
        db.refresh(questionnaire)
        return questionnaire
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create questionnaire: {str(e)}"
        )

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