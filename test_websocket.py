#!/usr/bin/env python3
"""
WebSocket功能测试脚本
测试从Redis获取数据并转发到WebSocket的功能
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.redis_client import RedisClient
from app.core.edge_data_client import EdgeDataClient
from app.models.edge_data import DataType

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redis_connection():
    """测试Redis连接"""
    print("🔍 测试Redis连接...")
    
    try:
        redis_client = RedisClient()
        await redis_client.connect()
        
        # 测试连接
        await redis_client.redis_client.ping()
        print(f"✅ Redis连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        
        return redis_client
        
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return None

async def test_edge_data_client(redis_client: RedisClient):
    """测试Edge数据客户端"""
    print("\n🔍 测试Edge数据客户端...")
    
    try:
        edge_client = EdgeDataClient(redis_client.redis_client)
        
        # 获取所有通道
        channels = await edge_client.get_all_channels()
        print(f"✅ 获取通道列表成功: {channels}")
        
        if channels:
            # 测试获取通道数据
            for channel_id in channels[:3]:  # 只测试前3个通道
                print(f"\n📊 测试通道 {channel_id}:")
                
                # 获取遥测数据
                telemetry_data = await edge_client.get_comsrv_data(channel_id, DataType.T)
                if telemetry_data:
                    print(f"  遥测数据: {telemetry_data}")
                else:
                    print("  遥测数据: 无数据")
                
                # 获取遥信数据
                signal_data = await edge_client.get_comsrv_data(channel_id, DataType.S)
                if signal_data:
                    print(f"  遥信数据: {signal_data}")
                else:
                    print("  遥信数据: 无数据")
                
                # 获取通道摘要
                summary = await edge_client.get_channel_data_summary(channel_id)
                print(f"  通道摘要: {summary}")
        
        return edge_client
        
    except Exception as e:
        print(f"❌ Edge数据客户端测试失败: {e}")
        return None

async def test_websocket_data_format():
    """测试WebSocket数据格式"""
    print("\n🔍 测试WebSocket数据格式...")
    
    try:
        from app.models.edge_data import (
            create_data_update_message, create_alarm_message,
            create_subscribe_ack_message, create_control_ack_message
        )
        
        # 测试数据更新消息
        data_update = create_data_update_message(1001, DataType.T, {"1": 25.5, "2": 380.2})
        print(f"✅ 数据更新消息: {data_update.json()}")
        
        # 测试告警消息
        alarm_msg = create_alarm_message("ALM_001", 1001, 1, 1, 2, 95.5, "温度过高")
        print(f"✅ 告警消息: {alarm_msg.json()}")
        
        # 测试订阅确认消息
        sub_ack = create_subscribe_ack_message("sub_001", [1001, 1002], [])
        print(f"✅ 订阅确认消息: {sub_ack.json()}")
        
        # 测试控制确认消息
        ctrl_ack = create_control_ack_message("ctrl_001", "CMD_001", "executed", True, 50.0)
        print(f"✅ 控制确认消息: {ctrl_ack.json()}")
        
        return True
        
    except Exception as e:
        print(f"❌ WebSocket数据格式测试失败: {e}")
        return False

async def test_redis_data_operations(edge_client: EdgeDataClient):
    """测试Redis数据操作"""
    print("\n🔍 测试Redis数据操作...")
    
    try:
        # 测试获取模型信息
        models = await edge_client.get_models_by_template("transformer")
        if models:
            print(f"✅ 获取变压器模型: {models}")
            
            # 测试获取模型定义
            for model_id in models[:2]:  # 只测试前2个模型
                model = await edge_client.get_modsrv_model(model_id)
                if model:
                    print(f"  模型 {model_id}: {model.name}")
                    
                    # 获取测量值
                    measurement = await edge_client.get_modsrv_measurement(model_id)
                    if measurement:
                        print(f"    测量值: {measurement.values}")
                    
                    # 获取控制值
                    action = await edge_client.get_modsrv_action(model_id)
                    if action:
                        print(f"    控制值: {action.values}")
        else:
            print("⚠️  未找到变压器模型")
        
        # 测试获取告警信息
        active_alarms = await edge_client.get_active_alarms()
        if active_alarms:
            print(f"✅ 活跃告警数量: {len(active_alarms)}")
            for alarm in active_alarms[:3]:  # 只显示前3个告警
                print(f"  告警 {alarm.alarm_id}: {alarm.title} - {alarm.level}")
        else:
            print("✅ 无活跃告警")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis数据操作测试失败: {e}")
        return False

async def simulate_websocket_data_flow(edge_client: EdgeDataClient):
    """模拟WebSocket数据流"""
    print("\n🔍 模拟WebSocket数据流...")
    
    try:
        # 获取所有通道
        channels = await edge_client.get_all_channels()
        if not channels:
            print("⚠️  没有可用的通道数据")
            return False
        
        print(f"📡 模拟数据推送，通道数量: {len(channels)}")
        
        # 模拟数据推送
        for i in range(3):  # 模拟3次推送
            print(f"\n🔄 第 {i+1} 次数据推送:")
            
            for channel_id in channels[:2]:  # 只模拟前2个通道
                updates = []
                
                # 获取各种类型的数据
                for data_type in DataType:
                    data = await edge_client.get_comsrv_data(channel_id, data_type)
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
                    
                    print(f"  通道 {channel_id}: {len(updates)} 个数据更新")
                    print(f"    消息ID: {batch_message['id']}")
                    print(f"    时间戳: {batch_message['timestamp']}")
                    
                    # 模拟发送到WebSocket客户端
                    message_json = json.dumps(batch_message, ensure_ascii=False, indent=2)
                    print(f"    消息内容: {message_json[:200]}...")
            
            # 等待1秒
            await asyncio.sleep(1)
        
        print("\n✅ WebSocket数据流模拟完成")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket数据流模拟失败: {e}")
        return False

async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行WebSocket功能测试...\n")
    
    # 测试Redis连接
    redis_client = await test_redis_connection()
    if not redis_client:
        print("❌ Redis连接失败，无法继续测试")
        return False
    
    try:
        # 测试Edge数据客户端
        edge_client = await test_edge_data_client(redis_client)
        if not edge_client:
            print("❌ Edge数据客户端测试失败")
            return False
        
        # 测试WebSocket数据格式
        format_success = await test_websocket_data_format()
        if not format_success:
            print("❌ WebSocket数据格式测试失败")
            return False
        
        # 测试Redis数据操作
        data_ops_success = await test_redis_data_operations(edge_client)
        if not data_ops_success:
            print("❌ Redis数据操作测试失败")
            return False
        
        # 模拟WebSocket数据流
        data_flow_success = await simulate_websocket_data_flow(edge_client)
        if not data_flow_success:
            print("❌ WebSocket数据流模拟失败")
            return False
        
        print("\n🎉 所有WebSocket功能测试通过！")
        print("\n📝 功能说明:")
        print("1. ✅ Redis连接成功")
        print("2. ✅ Edge数据获取正常")
        print("3. ✅ WebSocket消息格式正确")
        print("4. ✅ 数据推送流程正常")
        print("\n🚀 下一步:")
        print("1. 启动WebSocket服务: python main.py")
        print("2. 连接WebSocket: ws://localhost:6005/ws")
        print("3. 发送订阅消息获取实时数据")
        
        return True
        
    finally:
        # 关闭Redis连接
        await redis_client.close()
        print("\n🔌 Redis连接已关闭")

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试运行失败: {e}")
        sys.exit(1)
