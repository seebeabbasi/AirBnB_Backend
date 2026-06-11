from pydantic import BaseModel
from typing import Optional

class FamilyCreate(BaseModel):
    fullname: str
    relation: str
    age: int
    gender: str
    email: Optional[str]
    phonenumber: Optional[int]
    bio: Optional[str]

class FamilyUpdate(FamilyCreate):
    pass

class FamilyOut(FamilyCreate):
    id: int

    class Config:
        from_attributes = True