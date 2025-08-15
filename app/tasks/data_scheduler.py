"""
数据调度器
定时从Redis获取Edge数据并转发到WebSocket
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import schedule
import time

from app.core.redis_client import RedisClient
from app.websocket.websocket_manager import WebSocketManager
from app.core.config import settings
from app.models.response import WebSocketMessage
from app.models.edge_data import DataType
from app.core.edge_data_client import EdgeDataClient

logger = logging.getLogger(__name__)

class DataScheduler:
    """数据调度器"""
    
    def __init__(self, redis_client: RedisClient, websocket_manager: WebSocketManager):
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        self.edge_data_client = EdgeDataClient(redis_client.redis_client)
        self.running = False
        self.scheduler_task = None
        
    async def start(self):
        """启动数据调度器"""
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("数据调度器已启动")
    
    async def stop(self):
        """停止数据调度器"""
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("数据调度器已停止")
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        while self.running:
            try:
                # 检查是否有订阅的客户端
                if not self.websocket_manager:
                    await asyncio.sleep(1)
                    continue
                
                # 获取所有订阅信息
                subscriptions = self.websocket_manager.connection_manager.get_subscriptions()
                
                if not subscriptions:
                    # 没有订阅的客户端时，等待更长时间
                    await asyncio.sleep(5)
                    continue
                
                # 为每个订阅的客户端处理数据推送
                await self._process_subscriptions(subscriptions)
                
                # 使用较短的检查间隔，以便及时响应新的订阅
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"数据调度器循环出错: {e}")
                await asyncio.sleep(5)
    
    async def _process_subscriptions(self, subscriptions: dict):
        """处理所有订阅的数据推送"""
        try:
            current_time = time.time()
            
            for client_id, subscription in subscriptions.items():
                # 检查客户端是否仍然连接
                if client_id not in self.websocket_manager.connection_manager.active_connections:
                    continue
                
                # 获取客户端的推送间隔设置
                interval = subscription.get("interval", 5000)  # 默认5秒
                interval_seconds = interval / 1000.0  # 转换为秒
                
                # 检查是否到了推送时间
                last_push_key = f"last_push_{client_id}"
                last_push_time = getattr(self, last_push_key, 0)
                
                if current_time - last_push_time >= interval_seconds:
                    # 推送数据
                    await self._push_data_to_client(client_id, subscription)
                    # 更新最后推送时间
                    setattr(self, last_push_key, current_time)
                    
        except Exception as e:
            logger.error(f"处理订阅数据推送失败: {e}")
    
    def reset_client_push_time(self, client_id: str):
        """重置客户端的推送时间（用于初始推送后）"""
        last_push_key = f"last_push_{client_id}"
        setattr(self, last_push_key, time.time())
        logger.debug(f"重置客户端 {client_id} 的推送时间")
    
    async def _push_data_to_client(self, client_id: str, subscription: dict):
        """向特定客户端推送数据"""
        try:
            channels = subscription.get("channels", [])
            data_types = subscription.get("data_types", ["T"])
            
            if not channels:
                return
            
            # 为每个通道获取数据
            for channel_id in channels:
                updates = []
                
                # 获取各种类型的数据
                for data_type_str in data_types:
                    try:
                        data_type = DataType(data_type_str)
                        data = await self.edge_data_client.get_comsrv_data(channel_id, data_type)
                        
                        if data:
                            updates.append({
                                "channel_id": channel_id,
                                "data_type": data_type_str,
                                "values": data
                            })
                    except ValueError:
                        logger.warning(f"无效的数据类型: {data_type_str}")
                        continue
                
                if updates:
                    # 创建批量数据更新消息
                    batch_message = {
                        "type": "data_batch",
                        "id": f"batch_{channel_id}_{int(time.time())}",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "updates": updates
                        }
                    }
                    
                    # 向客户端推送数据
                    await self.websocket_manager.send_message(client_id, batch_message)
                    
                    logger.debug(f"已向客户端 {client_id} 推送通道 {channel_id} 的数据，更新数量: {len(updates)}")
                    
        except Exception as e:
            logger.error(f"向客户端 {client_id} 推送数据失败: {e}")
    
    async def _fetch_and_broadcast_edge_data(self):
        """获取并广播Edge数据"""
        try:
            # 获取所有通道
            channels = await self.edge_data_client.get_all_channels()
            
            if not channels:
                logger.debug("没有可用的通道数据")
                return
            
            # 为每个通道获取数据并推送
            for channel_id in channels:
                await self._process_channel_data(channel_id)
                
        except Exception as e:
            logger.error(f"获取并广播Edge数据失败: {e}")
    
    async def _process_channel_data(self, channel_id: int):
        """处理单个通道的数据"""
        try:
            updates = []
            
            # 获取各种类型的数据
            for data_type in DataType:
                data = await self.edge_data_client.get_comsrv_data(channel_id, data_type)
                
                if data:
                    updates.append({
                        "channel_id": channel_id,
                        "data_type": data_type.value,
                        "values": data
                    })
            
            if updates:
                # 创建批量数据更新消息
                batch_message = {
                    "type": "data_batch",
                    "id": f"batch_{channel_id}_{int(time.time())}",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "updates": updates
                    }
                }
                
                # 只向订阅了该通道的客户端推送数据
                await self._push_to_subscribed_clients(channel_id, batch_message)
                
                logger.debug(f"已处理通道 {channel_id} 的数据，更新数量: {len(updates)}")
            else:
                logger.debug(f"通道 {channel_id} 没有新数据")
                
        except Exception as e:
            logger.error(f"处理通道 {channel_id} 数据失败: {e}")
    
    async def _push_to_subscribed_clients(self, channel_id: int, message: dict):
        """向订阅了特定通道的客户端推送数据"""
        try:
            if not self.websocket_manager:
                return
            
            # 获取所有订阅信息
            subscriptions = self.websocket_manager.connection_manager.get_subscriptions()
            
            # 统计推送的客户端数量
            pushed_count = 0
            
            for client_id, subscription in subscriptions.items():
                # 检查客户端是否订阅了该通道
                if channel_id in subscription.get("channels", []):
                    try:
                        # 向订阅的客户端推送数据
                        await self.websocket_manager.send_message(client_id, message)
                        pushed_count += 1
                    except Exception as e:
                        logger.error(f"向客户端 {client_id} 推送数据失败: {e}")
            
            if pushed_count > 0:
                logger.info(f"已向 {pushed_count} 个订阅客户端推送通道 {channel_id} 的数据")
            else:
                logger.debug(f"通道 {channel_id} 没有订阅的客户端")
                
        except Exception as e:
            logger.error(f"推送数据到订阅客户端失败: {e}")
    
    async def fetch_specific_data(self, data_type: str) -> Optional[List[Dict[str, Any]]]:
        """获取指定类型的数据（兼容性方法）"""
        try:
            # 从Redis获取数据
            data = await self.redis_client.get_data_for_websocket(data_type)
            return data
        except Exception as e:
            logger.error(f"获取 {data_type} 数据失败: {e}")
            return None
    
    async def get_data_summary(self) -> Dict[str, Any]:
        """获取数据摘要"""
        try:
            summary = {
                "total_channels": 0,
                "data_types": list(DataType.__members__.keys()),
                "last_update": datetime.now().isoformat()
            }
            
            # 获取通道数量
            channels = await self.edge_data_client.get_all_channels()
            summary["total_channels"] = len(channels)
            
            return summary
            
        except Exception as e:
            logger.error(f"获取数据摘要失败: {e}")
            return {"error": str(e)}
    
    async def broadcast_custom_message(self, message_type: str, data: Any, data_type: str = "general"):
        """广播自定义消息"""
        try:
            message = WebSocketMessage(
                type=message_type,
                data=data
            )
            
            await self.websocket_manager.broadcast_message(message, data_type)
            logger.info(f"已广播自定义消息: {message_type}")
            
        except Exception as e:
            logger.error(f"广播自定义消息失败: {e}")
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "running": self.running,
            "data_types": list(DataType.__members__.keys()),
            "fetch_interval": settings.DATA_FETCH_INTERVAL,
            "last_run": datetime.now().isoformat()
        }
    
    def add_data_type(self, data_type: str):
        """添加新的数据类型"""
        if data_type not in DataType.__members__:
            logger.warning(f"尝试添加不支持的数据类型: {data_type}")
        else:
            logger.info(f"添加新的数据类型: {data_type}")
    
    def remove_data_type(self, data_type: str):
        """移除数据类型"""
        if data_type in DataType.__members__:
            logger.info(f"移除数据类型: {data_type}")
        else:
            logger.warning(f"尝试移除不支持的数据类型: {data_type}")
    
    async def manual_trigger(self, data_type: str = None):
        """手动触发数据获取"""
        try:
            if data_type:
                # 手动触发时，data_type 是具体的类型，如 "sensor", "metrics" 等
                # 需要转换为 DataType 枚举
                if data_type in DataType.__members__:
                    await self._process_channel_data(0) # 假设手动触发时 channel_id 为 0
                    logger.info(f"手动触发数据获取: {data_type}")
                else:
                    logger.warning(f"手动触发不支持的数据类型: {data_type}")
            else:
                # 手动触发所有数据获取
                await self._fetch_and_broadcast_edge_data()
                logger.info("手动触发所有数据获取")
        except Exception as e:
            logger.error(f"手动触发数据获取失败: {e}")

class MockDataGenerator:
    """模拟数据生成器（用于测试）"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
    
    async def generate_mock_data(self):
        """生成模拟数据"""
        try:
            # 生成传感器数据
            sensor_data = {
                "temperature": round(20 + (datetime.now().second / 60) * 10, 2),
                "humidity": round(50 + (datetime.now().second / 60) * 20, 2),
                "pressure": round(1013 + (datetime.now().second / 60) * 5, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            # 生成指标数据
            metrics_data = {
                "cpu_usage": round(30 + (datetime.now().second / 60) * 40, 2),
                "memory_usage": round(60 + (datetime.now().second / 60) * 30, 2),
                "disk_usage": round(45 + (datetime.now().second / 60) * 20, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            # 生成事件数据
            events_data = {
                "event_type": "system_check",
                "severity": "info",
                "message": f"系统检查完成 - {datetime.now().isoformat()}",
                "timestamp": datetime.now().isoformat()
            }
            
            # 存储到Redis
            await self.redis_client.set(
                f"{settings.REDIS_PREFIX}sensor",
                json.dumps([sensor_data]),
                expire=3600
            )
            
            await self.redis_client.set(
                f"{settings.REDIS_PREFIX}metrics",
                json.dumps([metrics_data]),
                expire=3600
            )
            
            await self.redis_client.set(
                f"{settings.REDIS_PREFIX}events",
                json.dumps([events_data]),
                expire=3600
            )
            
            logger.info("模拟数据生成完成")
            
        except Exception as e:
            logger.error(f"生成模拟数据失败: {e}")
    
    async def start_mock_data_generation(self, interval: int = 10):
        """启动模拟数据生成"""
        while True:
            try:
                await self.generate_mock_data()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"模拟数据生成循环出错: {e}")
                await asyncio.sleep(5)
