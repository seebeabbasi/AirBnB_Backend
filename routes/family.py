from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.database import get_db
from models.family import FamilyMember
from schemas.family import FamilyCreate, FamilyUpdate

router = APIRouter(prefix="/family", tags=["Family"])

# ADD FAMILY MEMBER
@router.post("/{user_id}")
async def add_family(user_id: int, data: FamilyCreate, db: AsyncSession = Depends(get_db)):
    member = FamilyMember(user_id=user_id, **data.dict())
    db.add(member)
    await db.commit()
    return {"message": "Family member added"}

# UPDATE FAMILY
@router.put("/{family_id}")
async def update_family(family_id: int, data: FamilyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FamilyMember).where(FamilyMember.id == family_id))
    member = result.scalar_one()

    for key, value in data.dict(exclude_unset=True).items():
        setattr(member, key, value)

    await db.commit()
    return {"message": "Updated"}

# DELETE FAMILY
@router.delete("/{family_id}")
async def delete_family(family_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FamilyMember).where(FamilyMember.id == family_id))
    member = result.scalar_one()

    await db.delete(member)
    await db.commit()
    return {"message": "Deleted"}