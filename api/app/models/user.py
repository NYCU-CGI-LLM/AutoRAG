from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import UUID, uuid4


class User(SQLModel, table=True):
    __tablename__ = "user"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_name: str = Field(..., max_length=100, unique=True, index=True)
    password: str = Field(..., max_length=255)  # Hashed password 