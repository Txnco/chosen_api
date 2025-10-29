

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case
from datetime import datetime, timedelta
from typing import List

from database import get_db
from auth.jwt import get_current_user, require_admin
from models.motivational_quote import MotivationalQuote
from schema.motivational_quote import (
    MotivationalQuoteCreate,
    MotivationalQuoteUpdate,
    MotivationalQuoteResponse,
    RandomQuoteResponse
)


quote_router = APIRouter(prefix="/quotes", tags=["Motivational Quotes"])


@quote_router.get('/random', response_model=RandomQuoteResponse)
def get_random_quote(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the daily motivational quote:
    - Returns the same quote for all users throughout the day (UTC-based)
    - Selects a new quote at midnight UTC
    - Prioritizes quotes that haven't been shown recently
    - Prioritizes quotes with fewer total views
    - Only returns active, non-deleted quotes
    """
    
    # Get current UTC date (without time)
    now = datetime.utcnow()
    today = now.date()
    
    # Check if there's a quote already selected for today
    # We'll use a simple approach: check if any quote was last_shown_at today
    todays_quote = db.query(MotivationalQuote).filter(
        and_(
            MotivationalQuote.is_active == True,
            MotivationalQuote.deleted_at == None,
            func.date(MotivationalQuote.last_shown_at) == today
        )
    ).first()
    
    if todays_quote:
        # Return the already selected quote for today
        return RandomQuoteResponse(
            id=todays_quote.id,
            quote=todays_quote.quote,
            author=todays_quote.author,
            times_shown=todays_quote.times_shown
        )
    
    # No quote selected for today yet, select a new one
    quotes = db.query(MotivationalQuote).filter(
        and_(
            MotivationalQuote.is_active == True,
            MotivationalQuote.deleted_at == None
        )
    ).all()
    
    if not quotes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active quotes available"
        )
    
    # If there are quotes that have never been shown, prioritize those
    never_shown = [q for q in quotes if q.times_shown == 0]
    if never_shown:
        # Randomly pick from never shown quotes
        import random
        selected_quote = random.choice(never_shown)
    else:
        # Use weighted random selection based on:
        # - Time since last shown (older gets higher weight)
        # - Times shown (less shown gets higher weight)
        
        import random
        
        # Calculate weights for each quote
        weights = []
        for quote in quotes:
            # Base weight (higher is better)
            weight = 100
            
            # Reduce weight based on times_shown (more shown = lower weight)
            weight -= min(quote.times_shown * 5, 50)  # Cap at 50 point reduction
            
            # Increase weight based on time since last shown
            if quote.last_shown_at:
                hours_since_shown = (now - quote.last_shown_at).total_seconds() / 3600
                # Add weight for each day since shown (max 50 points)
                weight += min(hours_since_shown / 24 * 10, 50)
            else:
                # Never shown, give maximum time bonus
                weight += 50
            
            # Ensure weight is at least 1
            weight = max(weight, 1)
            weights.append(weight)
        
        # Select quote using weighted random
        selected_quote = random.choices(quotes, weights=weights, k=1)[0]
    
    # Update the selected quote's stats for today
    selected_quote.times_shown += 1
    selected_quote.last_shown_at = now
    db.commit()
    db.refresh(selected_quote)
    
    return RandomQuoteResponse(
        id=selected_quote.id,
        quote=selected_quote.quote,
        author=selected_quote.author,
        times_shown=selected_quote.times_shown
    )


@quote_router.get('/', response_model=List[MotivationalQuoteResponse])
def get_all_quotes(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all motivational quotes (non-deleted)"""
    quotes = db.query(MotivationalQuote).filter(
        MotivationalQuote.deleted_at == None
    ).order_by(MotivationalQuote.created_at.desc()).all()
    
    return quotes


@quote_router.get('/{quote_id}', response_model=MotivationalQuoteResponse)
def get_quote_by_id(
    quote_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific motivational quote by ID"""
    quote = db.query(MotivationalQuote).filter(
        MotivationalQuote.id == quote_id,
        MotivationalQuote.deleted_at == None
    ).first()
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    return quote


@quote_router.post('/', response_model=MotivationalQuoteResponse, status_code=status.HTTP_201_CREATED)
def create_quote(
    quote_data: MotivationalQuoteCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new motivational quote (admin only)"""
    new_quote = MotivationalQuote(
        quote=quote_data.quote,
        author=quote_data.author,
        is_active=quote_data.is_active
    )
    
    db.add(new_quote)
    db.commit()
    db.refresh(new_quote)
    
    return new_quote


@quote_router.put('/{quote_id}', response_model=MotivationalQuoteResponse)
def update_quote(
    quote_id: int,
    quote_data: MotivationalQuoteUpdate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update an existing motivational quote (admin only)"""
    quote = db.query(MotivationalQuote).filter(
        MotivationalQuote.id == quote_id,
        MotivationalQuote.deleted_at == None
    ).first()
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Update only provided fields
    if quote_data.quote is not None:
        quote.quote = quote_data.quote
    if quote_data.author is not None:
        quote.author = quote_data.author
    if quote_data.is_active is not None:
        quote.is_active = quote_data.is_active
    
    db.commit()
    db.refresh(quote)
    
    return quote


@quote_router.delete('/{quote_id}')
def delete_quote(
    quote_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Soft delete a motivational quote (admin only)"""
    quote = db.query(MotivationalQuote).filter(
        MotivationalQuote.id == quote_id,
        MotivationalQuote.deleted_at == None
    ).first()
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Soft delete
    quote.deleted_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"Quote {quote_id} deleted successfully"}

