from enum import verify
import json
from fastapi import APIRouter, Depends,HTTPException,UploadFile, File, Form,status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import os, uuid
from core.database import get_db
from models.user import User
from schemas.user import UserCreate, UserLogin, UserUpdate
from models.family import FamilyMember


router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/signup")
async def signup(data: UserCreate, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = User(
        fullname=data.fullname,
        email=data.email,
        password_hash=data.password
    )
    db.add(user)
    await db.commit()
    return {
        "success": True,
        "message": "User created"
    }


@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .where(User.email == data.email)
        .options(selectinload(User.family_members))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.password_hash != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "success": True,
        "message": "Login success",
        "user": {
            "id": user.id,
            "fullname": user.fullname,
            "email": user.email,
            "phonenumber": user.phonenumber,
            "role": user.role,
            "gender": user.gender,
            "full_address": user.full_address,
            "bio": user.bio,
            "verification_status": user.verification_status,
            "profile_picture": user.profile_picture,
            "live_image_url": user.live_image_url,
            "cnic_front_url": user.cnic_front_url,
            "cnic_back_url": user.cnic_back_url,
            "passport_url": user.passport_url,
            "habbits": user.habbits,
            "family_members": [
                {
                    "id": fm.id,
                    "fullname": fm.fullname,
                    "relation": fm.relation,
                    "age": fm.age,
                    "gender": fm.gender,
                    "email": fm.email,
                    "phonenumber": fm.phonenumber,
                    "bio": fm.bio
                } for fm in user.family_members
            ]
        }
    }


@router.put("/profile_update_simple/{user_id}")
async def profile_update_simple(
    user_id: int,
    fullname: str = Form(None),
    email: str = Form(None),
    phonenumber: str = Form(None),
    gender: str = Form(None),
    full_address: str = Form(None),
    bio: str = Form(None),
    habbits: str = Form(None),
    family_members: str = Form(None),
    profile_picture: UploadFile = File(None),
    live_image: UploadFile = File(None),
    cnic_front: UploadFile = File(None),
    cnic_back: UploadFile = File(None),
    passport: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        # GET USER
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.family_members))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # UPDATE BASIC INFO
        if fullname: user.fullname = fullname
        if email: user.email = email
        if phonenumber: user.phonenumber = phonenumber
        if gender: user.gender = gender
        if full_address: user.full_address = full_address
        if bio: user.bio = bio

        # UPDATE HABBITS
        if habbits:
            try:
                user.habbits = json.loads(habbits)
            except:
                pass

        # UPLOAD FUNCTION
        async def save_image(file: UploadFile, folder: str):
            if not file: return None
            os.makedirs(folder, exist_ok=True)
            filename = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join(folder, filename)
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            return f"/{folder}/{filename}"

        if profile_picture: user.profile_picture = await save_image(profile_picture, "uploads/profile")
        if live_image: user.live_image_url = await save_image(live_image, "uploads/live")
        if cnic_front: user.cnic_front_url = await save_image(cnic_front, "uploads/cnic")
        if cnic_back: user.cnic_back_url = await save_image(cnic_back, "uploads/cnic")
        if passport: user.passport_url = await save_image(passport, "uploads/passport")

        # FAMILY MEMBERS
        if family_members:
            try:
                incoming = json.loads(family_members)
                print("INCOMING FAMILY MEMBERS:", incoming)  # ✅ DEBUG
                existing_members = {fm.id: fm for fm in user.family_members}
                print("EXISTING FAMILY MEMBERS:", existing_members)  # ✅ DEBUG
                incoming_ids = []

                for member in incoming:
                    member_id = member.get("id")
                    print("MEMBER ID:", member_id)  # ✅ DEBUG
                    age_val = member.get("age")
                    if age_val is not None and str(age_val).isdigit():
                        age_val = int(age_val)
                    else:
                        age_val = None

                    if member_id and member_id in existing_members:
                        # ✅ UPDATE existing member
                        fm = existing_members[member_id]
                        fm.fullname = member.get("fullname", fm.fullname)
                        fm.relation = member.get("relation", fm.relation)
                        fm.age = age_val if age_val is not None else fm.age
                        fm.gender = member.get("gender", fm.gender)
                        fm.email = member.get("email", fm.email)
                        fm.phonenumber = member.get("phonenumber", fm.phonenumber)
                        fm.bio = member.get("bio", fm.bio)
                        incoming_ids.append(member_id)
                    else:
                        # ✅ CREATE new member
                        new_member = FamilyMember(
                            fullname=member.get("fullname"),
                            relation=member.get("relation"),
                            age=age_val,
                            gender=member.get("gender"),
                            email=member.get("email"),
                            phonenumber=member.get("phonenumber"),
                            bio=member.get("bio"),
                            user_id=user.id
                        )
                        db.add(new_member)

                # ✅ DELETE only members removed by user
                for fm_id, fm in existing_members.items():
                    if fm_id not in incoming_ids:
                        await db.delete(fm)

            except Exception as e:
                print("Error saving family members", e)

        await db.commit()

        # RELOAD
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.family_members))
        )
        user = result.scalar_one()

        return {
            "success": True,
            "message": "User and family members updated successfully",
            "user": {
                "id": user.id,
                "fullname": user.fullname,
                "email": user.email,
                "phonenumber": user.phonenumber,
                "gender": user.gender,
                "full_address": user.full_address,
                "bio": user.bio,
                "role": user.role,
                "verification_status": user.verification_status,
                "profile_picture": user.profile_picture,
                "live_image_url": user.live_image_url,
                "cnic_front_url": user.cnic_front_url,
                "cnic_back_url": user.cnic_back_url,
                "passport_url": user.passport_url,
                "habbits": user.habbits,
                "family_members": [
                    {
                        "id": fm.id,
                        "fullname": fm.fullname,
                        "relation": fm.relation,
                        "age": fm.age,
                        "gender": fm.gender,
                        "email": fm.email,
                        "phonenumber": fm.phonenumber,
                        "bio": fm.bio
                    } for fm in user.family_members
                ]
            }
        }

    except Exception as e:
        print("Exception occurred:", e)
        raise HTTPException(status_code=500, detail=str(e))