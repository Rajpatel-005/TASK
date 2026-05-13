import os
from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, create_engine, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.schemas import UserResponse


def get_database_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "chat_app")
    user = os.getenv("POSTGRES_USER", "chat_user")
    password = os.getenv("POSTGRES_PASSWORD", "chat_password")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


engine = create_engine(get_database_url())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String(15), unique=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String(15), unique=True, nullable=False)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def get_postgres_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_postgres_tables():
    Base.metadata.create_all(bind=engine)


def serialize_user(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def get_or_create_user(db: Session, mobile_number: str):
    existing_user = db.query(User).filter(User.mobile_number == mobile_number).first()

    if existing_user:
        return serialize_user(existing_user), False

    new_user = User(mobile_number=mobile_number)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return serialize_user(new_user), True


def upsert_otp_code(db: Session, mobile_number: str, otp_code: str, expires_at: datetime):
    existing_otp = db.query(OTPCode).filter(OTPCode.mobile_number == mobile_number).first()

    if existing_otp:
        existing_otp.otp_code = otp_code
        existing_otp.expires_at = expires_at
        db.commit()
        db.refresh(existing_otp)
        return existing_otp

    new_otp = OTPCode(
        mobile_number=mobile_number,
        otp_code=otp_code,
        expires_at=expires_at,
    )
    db.add(new_otp)
    db.commit()
    db.refresh(new_otp)
    return new_otp


def get_otp_code(db: Session, mobile_number: str):
    return db.query(OTPCode).filter(OTPCode.mobile_number == mobile_number).first()


def delete_otp_code(db: Session, otp_record: OTPCode):
    db.delete(otp_record)
    db.commit()


def is_otp_expired(otp_record: OTPCode) -> bool:
    return datetime.now(timezone.utc) > otp_record.expires_at
