# Complete Guide: Adding New Database Tables in FastAPI

## Overview

This guide shows you exactly how to add a new database table to your FastAPI application. We'll use a **Workouts** table as an example, but you can follow the same steps for any table.

## Project Structure (Recommended)

```
your_project/
├── database.py                 # Database connection
├── main.py                     # FastAPI app and main routes
├── dependencies.py             # Auth and common dependencies
├── security.py                 # JWT and password utilities
├── models/                     # SQLAlchemy models (database tables)
│   ├── user.py
│   ├── role.py
│   ├── questionnaire.py
│   └── workout.py              # New model we'll create
├── schemas/                    # Pydantic models (API validation)
│   ├── user.py
│   ├── questionnaire.py
│   └── workout.py              # New schema we'll create
├── crud/                       # Database operations
│   ├── user.py
│   ├── questionnaire.py
│   └── workout.py              # New CRUD we'll create
├── routes/                     # API endpoints
│   ├── auth.py
│   ├── user.py
│   ├── questionnaire.py
│   └── workout.py              # New routes we'll create
├── alembic/                    # Database migrations
├── .env                        # Environment variables
└── requirements.txt
```

---

## Step-by-Step Process

### Step 1: Plan Your Database Table

Before coding, decide what your table needs:

**Example: Workouts Table**
```
Fields needed:
- id (primary key)
- user_id (foreign key to users)
- name (e.g., "Morning Cardio")
- description
- duration_minutes
- calories_burned
- workout_date
- created_at, updated_at
```

### Step 2: Create SQLAlchemy Model

**File: `models/workout.py`**

```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Workout(Base):
    __tablename__ = "workouts"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to users table
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Workout details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    calories_burned = Column(Float, nullable=True)
    workout_date = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship to User model
    user = relationship("User", back_populates="workouts")
```

**Don't forget to update your User model:**

```python
# In models/user.py - add this to your User class
workouts = relationship("Workout", back_populates="user")
```

### Step 3: Create Pydantic Schemas

**File: `schemas/workout.py`**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Base schema with common fields
class WorkoutBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    duration_minutes: Optional[int] = Field(None, gt=0, le=1440)  # Max 24 hours
    calories_burned: Optional[float] = Field(None, ge=0)
    workout_date: datetime

# Schema for creating (what client sends)
class WorkoutCreate(WorkoutBase):
    pass  # user_id comes from JWT token

# Schema for updating (all fields optional)
class WorkoutUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    duration_minutes: Optional[int] = Field(None, gt=0, le=1440)
    calories_burned: Optional[float] = Field(None, ge=0)
    workout_date: Optional[datetime] = None

# Schema for returning data (what API sends back)
class Workout(WorkoutBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### Step 4: Create CRUD Operations

**File: `crud/workout.py`**

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from models.workout import Workout
from schemas.workout import WorkoutCreate, WorkoutUpdate

class WorkoutCRUD:
    def create(self, db: Session, workout_data: WorkoutCreate, user_id: int) -> Workout:
        """Create a new workout"""
        db_workout = Workout(
            user_id=user_id,
            **workout_data.dict()
        )
        db.add(db_workout)
        db.commit()
        db.refresh(db_workout)
        return db_workout
    
    def get_by_id(self, db: Session, workout_id: int) -> Optional[Workout]:
        """Get workout by ID"""
        return db.query(Workout).filter(Workout.id == workout_id).first()
    
    def get_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Workout]:
        """Get all workouts for a user"""
        return (
            db.query(Workout)
            .filter(Workout.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update(self, db: Session, workout_id: int, workout_data: WorkoutUpdate) -> Optional[Workout]:
        """Update a workout"""
        db_workout = self.get_by_id(db, workout_id)
        if not db_workout:
            return None
        
        # Update only provided fields
        update_data = workout_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_workout, field, value)
        
        db.commit()
        db.refresh(db_workout)
        return db_workout
    
    def delete(self, db: Session, workout_id: int) -> bool:
        """Delete a workout"""
        db_workout = self.get_by_id(db, workout_id)
        if db_workout:
            db.delete(db_workout)
            db.commit()
            return True
        return False

# Create instance to use in routes
workout_crud = WorkoutCRUD()
```

### Step 5: Create API Routes

**File: `routes/workout.py`**

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from schemas.user import User
from schemas.workout import Workout, WorkoutCreate, WorkoutUpdate
from crud.workout import workout_crud

router = APIRouter(prefix="/workouts", tags=["workouts"])

@router.post("/", response_model=Workout, status_code=status.HTTP_201_CREATED)
def create_workout(
    workout_data: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new workout for the current user"""
    return workout_crud.create(db=db, workout_data=workout_data, user_id=current_user.id)

@router.get("/", response_model=List[Workout])
def get_my_workouts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all workouts for the current user"""
    return workout_crud.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)

@router.get("/{workout_id}", response_model=Workout)
def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific workout"""
    workout = workout_crud.get_by_id(db, workout_id=workout_id)
    
    # Business logic: Check if workout exists
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Workout not found"
        )
    
    # Security: Make sure user owns this workout
    if workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this workout"
        )
    
    return workout

@router.put("/{workout_id}", response_model=Workout)
def update_workout(
    workout_id: int,
    workout_data: WorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a workout"""
    # Security check: Make sure workout exists and belongs to user
    existing_workout = workout_crud.get_by_id(db, workout_id=workout_id)
    if not existing_workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    if existing_workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this workout"
        )
    
    # Update the workout
    updated_workout = workout_crud.update(db, workout_id, workout_data)
    return updated_workout

@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a workout"""
    # Security check: Make sure workout exists and belongs to user
    existing_workout = workout_crud.get_by_id(db, workout_id=workout_id)
    if not existing_workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    if existing_workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this workout"
        )
    
    # Delete the workout
    success = workout_crud.delete(db, workout_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workout"
        )
```

### Step 6: Register Routes in Main App

**In `main.py`:**

```python
from fastapi import FastAPI
from routes import workout

app = FastAPI(title="Chosen API")

# Include workout routes
app.include_router(workout.router)

# Your other routes...
```

### Step 7: Update Alembic for Migration

**Update `alembic/env.py`:**

```python
# Import your new model so Alembic can see it
from models.workout import Workout
```

### Step 8: Create and Apply Migration

```bash
# Create migration
alembic revision --autogenerate -m "Add workouts table"

# Apply migration
alembic upgrade head
```

---

## Quick Reference: Order of Operations

1. ✅ **Plan** your table structure
2. ✅ **Model** (`models/workout.py`) - Define database table
3. ✅ **Schema** (`schemas/workout.py`) - Define API validation
4. ✅ **CRUD** (`crud/workout.py`) - Define database operations
5. ✅ **Routes** (`routes/workout.py`) - Define API endpoints
6. ✅ **Register** routes in `main.py`
7. ✅ **Migration** - Create and apply with Alembic

---

## Key Concepts Recap

### Models (SQLAlchemy)
- Define database table structure
- Handle relationships between tables
- **Pure database representation**

### Schemas (Pydantic)  
- Validate incoming data
- Serialize outgoing data
- Generate automatic API documentation
- **API contract definition**

### CRUD
- Simple database operations only
- No business logic
- Reusable across different endpoints
- **Database worker functions**

### Routes
- Business logic and validation
- Security and authorization
- Error handling
- HTTP response formatting
- **Smart business managers**

---

## Common Patterns

### Foreign Key Relationships
```python
# In model
user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
user = relationship("User", back_populates="workouts")
```

### Optional vs Required Fields
```python
# Required
name = Column(String(100), nullable=False)

# Optional  
description = Column(Text, nullable=True)
```

### Schema Inheritance
```python
class WorkoutBase(BaseModel):
    # Common fields

class WorkoutCreate(WorkoutBase):
    pass  # Inherits all fields from base

class Workout(WorkoutBase):
    # Inherits base fields + adds more
    id: int
    created_at: datetime
```

### Security Pattern
```python
# Always check ownership
if resource.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not authorized")
```

---

## Testing Your New Endpoints

Once everything is set up, you can test your new API:

```bash
# Start your FastAPI server
uvicorn main:app --reload

# Visit http://localhost:8000/docs
# You'll see your new workout endpoints in the Swagger UI
```

**Example API calls:**
- `POST /workouts/` - Create workout
- `GET /workouts/` - Get user's workouts  
- `GET /workouts/1` - Get specific workout
- `PUT /workouts/1` - Update workout
- `DELETE /workouts/1` - Delete workout

That's it! Follow these steps for any new table you want to add to your FastAPI application.