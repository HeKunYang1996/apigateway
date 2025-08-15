#!/bin/bash

# API网关启动脚本 - 简化版
# 适用于aarch64架构的工控机

echo "🚀 启动API网关..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Redis连接
echo "🔍 检查Redis连接..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ 本地Redis连接正常"
    else
        echo "⚠️  本地Redis未启动，请确保Redis服务运行"
    fi
else
    echo "⚠️  未找到redis-cli，请确保Redis已安装并运行"
fi

# 智能选择可用的镜像版本
echo "🔍 查找可用的镜像版本..."

# 查找所有voltageems-apigateway镜像
AVAILABLE_IMAGES=$(docker images --format "table {{.Repository}}:{{.Tag}}" | grep "voltageems-apigateway" | grep -v "REPOSITORY" | head -10)

if [ -z "$AVAILABLE_IMAGES" ]; then
    echo "❌ 未找到voltageems-apigateway镜像"
    echo "💡 请先运行 ./load_image.sh 加载镜像"
    exit 1
fi

echo "📋 可用的镜像版本:"
echo "$AVAILABLE_IMAGES"

# 智能选择镜像优先级：latest > 最新版本号 > 第一个可用的
IMAGE_NAME=""
if echo "$AVAILABLE_IMAGES" | grep -q "voltageems-apigateway:latest"; then
    IMAGE_NAME="voltageems-apigateway:latest"
    echo "✅ 使用latest版本"
else
    # 尝试找到版本号最高的镜像
    VERSIONED_IMAGES=$(echo "$AVAILABLE_IMAGES" | grep -E "voltageems-apigateway:[0-9]+\.[0-9]+\.[0-9]+")
    if [ -n "$VERSIONED_IMAGES" ]; then
        # 按版本号排序，选择最新的
        IMAGE_NAME=$(echo "$VERSIONED_IMAGES" | sort -V -r | head -1)
        echo "✅ 使用最新版本: $IMAGE_NAME"
    else
        # 选择第一个可用的镜像
        IMAGE_NAME=$(echo "$AVAILABLE_IMAGES" | head -1)
        echo "✅ 使用可用镜像: $IMAGE_NAME"
    fi
fi

# 停止现有容器
echo "🛑 停止现有容器..."
docker stop voltageems-apigateway 2>/dev/null || true
docker rm voltageems-apigateway 2>/dev/null || true

# 启动服务（使用host网络模式）
echo "🚀 启动API网关服务..."
echo "🏷️  使用镜像: $IMAGE_NAME"
docker run -d \
    --name voltageems-apigateway \
    --network=host \
    --restart=unless-stopped \
    -v /extp/logs:/app/logs \
    -e REDIS_HOST=localhost \
    -e REDIS_PORT=6379 \
    -e REDIS_DB=0 \
    -e JWT_SECRET_KEY=your-secret-key-here-change-in-production \
    -e DEBUG=false \
    "$IMAGE_NAME"

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "🔍 检查服务状态..."
if curl -f http://localhost:6005/health > /dev/null 2>&1; then
    echo "✅ API网关启动成功！"
    echo "📱 服务地址: http://localhost:6005"
    echo "🔌 WebSocket: ws://localhost:6005/ws"
    echo "📊 健康检查: http://localhost:6005/health"
else
    echo "❌ 服务启动失败，请检查日志"
    docker logs voltageems-apigateway
    exit 1
fi

echo "🎉 启动完成！"
echo "🔧 管理命令:"
echo "   查看日志: docker logs voltageems-apigateway"
echo "   停止服务: docker stop voltageems-apigateway"
echo "   重启服务: docker restart voltageems-apigateway"
