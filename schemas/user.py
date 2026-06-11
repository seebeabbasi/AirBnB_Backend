from pydantic import BaseModel
from typing import Optional, List


class UserCreate(BaseModel):
    fullname: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserUpdate(BaseModel):
    fullname: Optional[str]
    email: Optional[str]
    phonenumber: Optional[str]
    role: Optional[str]
    profile_picture: Optional[str]
    verification_status: Optional[str]

    gender: Optional[str]
    full_address: Optional[str]
    bio: Optional[str]
    habbits: Optional[List[str]]

    live_image_url: Optional[str]
    cnic_front_url: Optional[str]
    cnic_back_url: Optional[str]
    passport_url: Optional[str]

class UserOut(BaseModel):
    id: int
    fullname: str
    email: str
    role: str
    profile_picture: Optional[str] = None
    verification_status: Optional[str] = None
    live_image_url: Optional[str] = None
    cnic_front_url: Optional[str] = None
    cnic_back_url: Optional[str] = None
    passport_url: Optional[str] = None

    class Config:
        from_attributes = True