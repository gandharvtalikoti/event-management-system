from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.schemas.user import UserCreate, UserRead, Token
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token
from app.core.database import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, session: Session = Depends(get_session)):
    hashed = hash_password(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed)
    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")

@router.post("/login", response_model=Token)
def login(user: UserCreate, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}
