#!/usr/bin/env python3
"""
测试认证功能
"""

import asyncio
import logging
from app.services.database import initialize_database
from app.services.user_service import get_user_service
from app.models.auth import UserLogin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_login():
    """测试登录功能"""
    try:
        # 初始化数据库
        await initialize_database()
        
        # 获取用户服务
        user_service = get_user_service()
        
        # 测试登录
        login_data = UserLogin(username="admin", password="admin123")
        tokens = await user_service.authenticate_user(login_data)
        
        print(f"登录成功！")
        print(f"访问令牌: {tokens.access_token[:50]}...")
        print(f"刷新令牌: {tokens.refresh_token[:50]}...")
        print(f"令牌类型: {tokens.token_type}")
        print(f"过期时间: {tokens.expires_in}秒")
        
        return True
        
    except Exception as e:
        print(f"登录失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_login())
    if success:
        print("✅ 认证测试通过")
    else:
        print("❌ 认证测试失败")
