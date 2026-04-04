from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    referred_by: int | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str
