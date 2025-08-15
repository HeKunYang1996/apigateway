"""
统一响应模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List, Generic, TypeVar
from datetime import datetime
import json

T = TypeVar('T')

def datetime_now():
    """获取当前时间的工厂函数"""
    return datetime.now()

class SafeJSONEncoder(json.JSONEncoder):
    """安全的JSON编码器，避免循环引用"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            # 避免循环引用
            return str(obj)
        return super().default(obj)

class ResponseModel(BaseModel, Generic[T]):
    """统一响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[T] = None
    timestamp: datetime = Field(default_factory=datetime_now)
    code: int = 200

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    message: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime_now)

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    success: bool = True
    message: str = "获取成功"
    data: List[T]
    pagination: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime_now)
    code: int = 200

class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str
    data: Any
    timestamp: datetime = Field(default_factory=datetime_now)
    message_id: Optional[str] = None

class DataResponse(BaseModel):
    """数据响应模型"""
    data_type: str
    data: Any
    timestamp: datetime = Field(default_factory=datetime_now)
    source: Optional[str] = None
