#!/usr/bin/env python3
"""
初始化管理员用户脚本
"""

import asyncio
import logging
import os
from app.services.database import initialize_database, get_database, DatabaseManager
from app.services.auth_service import get_auth_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_admin_user():
    """创建默认管理员用户"""
    try:
        # 使用默认路径初始化数据库（会自动检测环境）
        await initialize_database()
        
        db = get_database()
        auth = get_auth_service()
        
        # 检查是否已存在管理员用户
        admin_user = await db.get_user_by_username("admin")
        if admin_user:
            logger.info("管理员用户已存在，跳过创建")
            return
        
        # 创建管理员用户
        password_hash = auth.hash_password("admin123")
        user_id = await db.create_user(
            username="admin",
            email="admin@voltageems.com",
            password_hash=password_hash,
            role_id=1  # 管理员角色
        )
        
        logger.info(f"管理员用户创建成功 (ID: {user_id})")
        logger.info("默认登录信息:")
        logger.info("  用户名: admin")
        logger.info("  密码: admin123")
        logger.info("  邮箱: admin@voltageems.com")
        logger.info("⚠️ 请尽快修改默认密码！")
        
    except Exception as e:
        logger.error(f"创建管理员用户失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_admin_user())
