"""
用户相关数据模型
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    """用户创建模型"""
    password: str

class UserUpdate(BaseModel):
    """用户更新模型"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    """用户模型"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str

class Token(BaseModel):
    """令牌模型"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = None
