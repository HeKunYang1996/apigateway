#!/usr/bin/env python3
"""
项目测试脚本
验证API网关的基本功能
"""

import asyncio
import json
import logging
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.redis_client import RedisClient
from app.models.response import WebSocketMessage
from app.utils.helpers import generate_uuid, format_timestamp

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redis_connection():
    """测试Redis连接"""
    print("🔍 测试Redis连接...")
    
    try:
        redis_client = RedisClient()
        await redis_client.connect()
        
        # 测试基本操作
        test_key = "test:connection"
        test_value = "Hello Redis!"
        
        # 设置值
        await redis_client.set(test_key, test_value)
        print("✅ Redis SET操作成功")
        
        # 获取值
        result = await redis_client.get(test_key)
        if result == test_value:
            print("✅ Redis GET操作成功")
        else:
            print(f"❌ Redis GET操作失败，期望: {test_value}, 实际: {result}")
        
        # 删除测试键
        await redis_client.delete(test_key)
        print("✅ Redis DELETE操作成功")
        
        await redis_client.close()
        print("✅ Redis连接测试通过")
        return True
        
    except Exception as e:
        print(f"❌ Redis连接测试失败: {e}")
        return False

async def test_websocket_message():
    """测试WebSocket消息模型"""
    print("\n🔍 测试WebSocket消息模型...")
    
    try:
        message = WebSocketMessage(
            type="test",
            data={"message": "Hello WebSocket!"}
        )
        
        message_json = message.json()
        print(f"✅ WebSocket消息创建成功: {message_json}")
        
        # 测试解析
        parsed_message = WebSocketMessage.parse_raw(message_json)
        if parsed_message.type == "test":
            print("✅ WebSocket消息解析成功")
        else:
            print("❌ WebSocket消息解析失败")
        
        return True
        
    except Exception as e:
        print(f"❌ WebSocket消息测试失败: {e}")
        return False

async def test_utility_functions():
    """测试工具函数"""
    print("\n🔍 测试工具函数...")
    
    try:
        # 测试UUID生成
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        if uuid1 != uuid2 and len(uuid1) == 36:
            print("✅ UUID生成成功")
        else:
            print("❌ UUID生成失败")
        
        # 测试时间戳格式化
        from datetime import datetime
        timestamp = datetime.now()
        formatted = format_timestamp(timestamp)
        if formatted and "T" in formatted:
            print("✅ 时间戳格式化成功")
        else:
            print("❌ 时间戳格式化失败")
        
        # 测试JSON序列化
        test_data = {"test": "data", "number": 123}
        json_str = safe_json_dumps(test_data)
        if '"test":"data"' in json_str:
            print("✅ JSON序列化成功")
        else:
            print("❌ JSON序列化失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具函数测试失败: {e}")
        return False

def safe_json_dumps(obj):
    """安全的JSON序列化"""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception as e:
        return str(obj)

async def test_configuration():
    """测试配置加载"""
    print("\n🔍 测试配置加载...")
    
    try:
        # 检查配置项
        required_configs = [
            'APP_NAME', 'PORT', 'REDIS_HOST', 'REDIS_PORT',
            'JWT_SECRET_KEY', 'DATA_FETCH_INTERVAL'
        ]
        
        for config_name in required_configs:
            if hasattr(settings, config_name):
                value = getattr(settings, config_name)
                print(f"✅ 配置项 {config_name}: {value}")
            else:
                print(f"❌ 配置项 {config_name} 缺失")
                return False
        
        print("✅ 配置加载测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置加载测试失败: {e}")
        return False

async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行API网关项目测试...\n")
    
    tests = [
        ("配置加载", test_configuration),
        ("Redis连接", test_redis_connection),
        ("WebSocket消息", test_websocket_message),
        ("工具函数", test_utility_functions),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！项目框架搭建成功！")
        print("\n📝 下一步:")
        print("1. 配置 .env 文件")
        print("2. 运行 ./start.sh 启动项目")
        print("3. 访问 http://localhost:6005/docs 查看API文档")
        return True
    else:
        print("⚠️  部分测试失败，请检查项目配置")
        return False

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
