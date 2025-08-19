#!/bin/bash

# API网关部署验证脚本
# 验证服务是否正常运行

echo "🔍 API网关部署验证"
echo "===================="

# 检查Docker是否安装
echo "1. 检查Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    exit 1
else
    echo "✅ Docker已安装: $(docker --version)"
fi

# 检查容器是否运行
echo ""
echo "2. 检查容器状态..."
if docker ps | grep -q "voltageems-apigateway"; then
    echo "✅ 容器正在运行"
    docker ps | grep "voltageems-apigateway"
else
    echo "❌ 容器未运行"
    echo "💡 请运行 ./start.sh 启动服务"
    exit 1
fi

# 检查端口监听
echo ""
echo "3. 检查端口监听..."
if netstat -tlnp 2>/dev/null | grep -q ":6005"; then
    echo "✅ 端口6005正在监听"
else
    echo "❌ 端口6005未监听"
fi

# 检查健康检查端点
echo ""
echo "4. 检查健康检查..."
if curl -f -s http://localhost:6005/health > /dev/null 2>&1; then
    echo "✅ 健康检查通过"
    echo "📊 健康状态:"
    curl -s http://localhost:6005/health | python3 -m json.tool 2>/dev/null || echo "响应格式异常"
else
    echo "❌ 健康检查失败"
    echo "💡 请检查服务日志: docker logs voltageems-apigateway"
fi

# 检查配置目录
echo ""
echo "5. 检查配置目录..."
if [ -d "/extp/config" ]; then
    echo "✅ 配置目录存在: /extp/config"
    if [ -f "/extp/config/voltageems.db" ]; then
        echo "✅ 数据库文件存在"
        echo "📊 数据库大小: $(du -h /extp/config/voltageems.db | cut -f1)"
    else
        echo "⚠️  数据库文件不存在，可能是首次启动"
    fi
else
    echo "❌ 配置目录不存在"
fi

# 检查日志目录
echo ""
echo "6. 检查日志目录..."
if [ -d "/extp/logs" ]; then
    echo "✅ 日志目录存在: /extp/logs"
    if [ -f "/extp/logs/apigateway.log" ]; then
        echo "✅ 日志文件存在"
        echo "📊 日志大小: $(du -h /extp/logs/apigateway.log | cut -f1)"
        echo "📝 最近日志:"
        tail -5 /extp/logs/apigateway.log 2>/dev/null || echo "无法读取日志文件"
    else
        echo "⚠️  日志文件不存在"
    fi
else
    echo "❌ 日志目录不存在"
fi

# 测试认证API
echo ""
echo "7. 测试认证API..."
if curl -f -s -X POST http://localhost:6005/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}' > /dev/null 2>&1; then
    echo "✅ 认证API正常"
    echo "🔐 默认管理员账户可用"
else
    echo "❌ 认证API异常"
    echo "💡 请检查服务状态和日志"
fi

# 检查Redis连接
echo ""
echo "8. 检查Redis连接..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis连接正常"
    else
        echo "❌ Redis连接失败"
        echo "💡 请确保Redis服务运行在localhost:6379"
    fi
else
    echo "⚠️  redis-cli未安装，无法测试Redis连接"
fi

echo ""
echo "===================="
echo "🎉 验证完成！"
echo ""
echo "📱 服务访问地址:"
echo "   - API网关: http://localhost:6005"
echo "   - WebSocket: ws://localhost:6005/ws"
echo "   - 健康检查: http://localhost:6005/health"
echo "   - API文档: http://localhost:6005/docs"
echo ""
echo "🔐 默认管理员账户:"
echo "   - 用户名: admin"
echo "   - 密码: admin123"
echo "   - ⚠️  请尽快修改默认密码！"
