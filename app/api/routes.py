"""
主要API路由文件
包含所有接口定义，具体实现在其他文件中
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any

from app.middleware.auth import get_current_active_user
from app.models.response import ResponseModel, ErrorResponse
from app.core.redis_client import RedisClient

# 创建主路由
api_router = APIRouter()

# 安全认证
security = HTTPBearer()

# 全局Redis客户端（将在main.py中初始化）
redis_client: RedisClient = None

def get_redis_client() -> RedisClient:
    """获取Redis客户端实例"""
    if redis_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis客户端未初始化"
        )
    return redis_client

# ==================== 认证相关接口已移至 /api/v1/auth 路由 ====================

# ==================== 数据查询接口 ====================

@api_router.get("/data/{data_type}", response_model=ResponseModel[List[Dict[str, Any]]])
async def get_data(
    data_type: str,
    limit: int = 100,
    offset: int = 0,
    redis_client: RedisClient = Depends(get_redis_client)
):
    """
    获取指定类型的数据
    
    - **data_type**: 数据类型 (T-遥测, S-遥信, C-控制, A-调节)
    - **limit**: 返回数据数量限制
    - **offset**: 数据偏移量
    """
    try:
        from app.core.edge_data_client import EdgeDataClient
        edge_client = EdgeDataClient(redis_client)
        
        # 获取可用通道
        channels = await edge_client.get_all_channels()
        if not channels:
            return ResponseModel(
                success=True,
                message="暂无可用通道",
                data=[]
            )
        
        # 获取数据
        result_data = []
        for channel_id in channels[:limit]:  # 限制通道数量
            try:
                channel_data = await edge_client.get_channel_data_summary(channel_id)
                if channel_data and data_type.lower() in channel_data:
                    result_data.append({
                        "channel_id": channel_id,
                        "data_type": data_type,
                        "data": channel_data[data_type.lower()]
                    })
            except Exception as e:
                continue
        
        return ResponseModel(
            success=True,
            message=f"获取{data_type}类型数据成功",
            data=result_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据失败: {str(e)}"
        )

@api_router.get("/data/{data_type}/latest", response_model=ResponseModel[Dict[str, Any]])
async def get_latest_data(
    data_type: str,
    redis_client: RedisClient = Depends(get_redis_client)
):
    """
    获取指定类型的最新数据
    
    - **data_type**: 数据类型 (T-遥测, S-遥信, C-控制, A-调节)
    """
    try:
        from app.core.edge_data_client import EdgeDataClient
        edge_client = EdgeDataClient(redis_client)
        
        # 获取可用通道
        channels = await edge_client.get_all_channels()
        if not channels:
            return ResponseModel(
                success=True,
                message="暂无可用通道",
                data={}
            )
        
        # 获取第一个通道的最新数据
        channel_id = channels[0]
        channel_data = await edge_client.get_channel_data_summary(channel_id)
        
        if channel_data and data_type.lower() in channel_data:
            return ResponseModel(
                success=True,
                message=f"获取{data_type}类型最新数据成功",
                data={
                    "channel_id": channel_id,
                    "data_type": data_type,
                    "data": channel_data[data_type.lower()],
                    "timestamp": channel_data.get("timestamp", "")
                }
            )
        else:
            return ResponseModel(
                success=True,
                message=f"暂无{data_type}类型数据",
                data={}
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最新数据失败: {str(e)}"
        )

@api_router.get("/data/{data_type}/stats", response_model=ResponseModel[Dict[str, Any]], include_in_schema=False)
async def get_data_stats(
    data_type: str,
    redis_client: RedisClient = Depends(get_redis_client)
):
    """
    获取指定类型数据的统计信息
    """
    # 具体实现在 data.py 中
    pass

# ==================== 系统管理接口 ====================

@api_router.get("/system/status", response_model=ResponseModel[Dict[str, Any]])
async def get_system_status():
    """
    获取系统状态
    """
    try:
        import time
        import psutil
        
        # 获取系统信息
        system_info = {
            "timestamp": time.time(),
            "uptime": time.time() - psutil.boot_time(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            }
        }
        
        # 检查服务状态
        services = {
            "redis": "connected" if redis_client and redis_client.is_connected() else "disconnected",
            "database": "connected",  # 数据库连接状态
            "websocket": "active"      # WebSocket状态
        }
        
        return ResponseModel(
            success=True,
            message="系统状态获取成功",
            data={
                "system": system_info,
                "services": services,
                "status": "healthy"
            }
        )
        
    except Exception as e:
        return ResponseModel(
            success=False,
            message=f"获取系统状态失败: {str(e)}",
            data={"status": "error"}
        )

@api_router.get("/system/health", response_model=ResponseModel[Dict[str, Any]], include_in_schema=False)
async def get_system_health():
    """
    获取系统健康状态
    """
    # 具体实现在 system.py 中
    pass

@api_router.get("/system/metrics", response_model=ResponseModel[Dict[str, Any]], include_in_schema=False)
async def get_system_metrics():
    """
    获取系统指标
    """
    # 具体实现在 system.py 中
    pass

# ==================== 配置管理接口 ====================

@api_router.get("/config", response_model=ResponseModel[Dict[str, Any]], include_in_schema=False)
async def get_config():
    """
    获取系统配置
    """
    # 具体实现在 config.py 中
    pass

@api_router.put("/config", response_model=ResponseModel[Dict[str, Any]], include_in_schema=False)
async def update_config(
    config: Dict[str, Any],
    current_user: dict = Depends(get_current_active_user)
):
    """
    更新系统配置
    """
    # 具体实现在 config.py 中
    pass

# ==================== 日志查询接口 ====================

@api_router.get("/logs", response_model=ResponseModel[List[Dict[str, Any]]], include_in_schema=False)
async def get_logs(
    level: str = "INFO",
    limit: int = 100,
    offset: int = 0,
    start_time: str = None,
    end_time: str = None
):
    """
    获取系统日志
    """
    # 具体实现在 logs.py 中
    pass

# ==================== 工具接口 ====================

@api_router.post("/utils/validate", response_model=ResponseModel[Dict[str, Any]], include_in_schema=False)
async def validate_data(data: Dict[str, Any]):
    """
    数据验证工具
    """
    # 具体实现在 utils.py 中
    pass

@api_router.post("/utils/transform", response_model=ResponseModel[Dict[str, Any]], include_in_schema=False)
async def transform_data(
    data: Dict[str, Any],
    transform_type: str
):
    """
    数据转换工具
    """
    # 具体实现在 utils.py 中
    pass

# ==================== WebSocket状态接口 ====================

@api_router.get("/websocket/status", response_model=ResponseModel[Dict[str, Any]])
async def get_websocket_status():
    """
    获取WebSocket连接状态
    """
    try:
        from main import websocket_manager
        
        if websocket_manager is None:
            return ResponseModel(
                success=False,
                message="WebSocket管理器未初始化",
                data={"status": "unavailable"}
            )
        
        # 获取连接统计
        connection_count = len(websocket_manager.connection_manager.active_connections)
        
        return ResponseModel(
            success=True,
            message="WebSocket状态获取成功",
            data={
                "status": "active",
                "total_connections": connection_count,
                "active_clients": list(websocket_manager.connection_manager.active_connections.keys())
            }
        )
        
    except Exception as e:
        return ResponseModel(
            success=False,
            message=f"获取WebSocket状态失败: {str(e)}",
            data={"status": "error"}
        )

@api_router.get("/websocket/connections", response_model=ResponseModel[List[Dict[str, Any]]], include_in_schema=False)
async def get_websocket_connections():
    """
    获取所有WebSocket连接信息
    """
    # 具体实现在 websocket.py 中
    pass
