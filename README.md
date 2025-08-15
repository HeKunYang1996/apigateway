# API网关项目

一个基于Python FastAPI的统一API入口，提供身份认证、请求路由和实时数据WebSocket接口。

## 🌟 功能特性

- 🔐 **统一身份认证**: JWT令牌认证，支持用户注册、登录和令牌刷新
- 🚀 **API路由管理**: 统一的API入口，支持多种数据类型的查询和管理
- 📡 **实时WebSocket**: 支持实时数据推送和客户端连接管理
- 🔄 **数据调度**: 定时从Redis获取数据并转发到WebSocket客户端
- 🏭 **Edge数据支持**: 完整的Edge数据结构支持，包括遥测、遥信、遥控、遥调
- 🐳 **Docker支持**: 完整的Docker配置，支持aarch64架构
- 📊 **系统监控**: 系统状态、健康检查和指标监控

## 📋 技术栈

- **后端框架**: FastAPI 0.104.1
- **异步支持**: asyncio
- **数据存储**: Redis 5.0.1
- **认证**: JWT
- **WebSocket**: FastAPI WebSocket
- **容器化**: Docker
- **架构支持**: aarch64 (ARM64)

## 📁 项目结构

```
apigateway/
├── app/                           # 应用代码
│   ├── api/                       # API路由
│   ├── core/                      # 核心模块
│   ├── models/                    # 数据模型
│   ├── websocket/                 # WebSocket模块
│   ├── tasks/                     # 任务模块
│   └── utils/                     # 工具模块
├── main.py                        # 主程序入口
├── requirements.txt               # Python依赖
├── Dockerfile                     # Docker构建文件
├── start_websocket.sh             # 本地开发测试脚本
├── test_websocket.py              # WebSocket功能测试
├── websocket_client_test.html     # WebSocket客户端测试工具
├── env.example                    # 环境配置示例
├── env.development                # 开发环境配置
├── env.production                 # 生产环境配置
├── logs/                          # 日志目录
└── packages/                      # 部署包目录
    ├── voltageems-apigateway-*.tar.gz  # 预构建的Docker镜像
    ├── start.sh                   # 工控机启动脚本
    ├── load_image.sh              # 镜像加载脚本
    ├── build_image.sh             # 镜像构建脚本
    └── README.md                  # 部署说明
```

## 🚀 快速开始

### 本地开发测试

```bash
# 启动本地开发环境（自动安装依赖、配置环境、启动服务）
./start_websocket.sh
```

### 工控机部署

```bash
# 1. 进入packages目录
cd packages

# 2. 加载Docker镜像
./load_image.sh

# 3. 启动服务
./start.sh
```

## 🔧 Docker镜像构建

### 在开发机器上构建

```bash
cd packages
# 构建aarch64格式的镜像（版本号从config.py自动读取）
./build_image.sh
```

### 镜像信息

- **输出文件**: `packages/voltageems-apigateway-*.tar.gz`
- **目标架构**: aarch64 (ARM64)
- **适用环境**: Linux工控机
- **镜像大小**: ~400MB（已优化）

## 📱 服务访问

- **API网关**: http://localhost:6005
- **API文档**: http://localhost:6005/docs
- **健康检查**: http://localhost:6005/health
- **WebSocket**: ws://localhost:6005/ws
- **WebSocket状态**: http://localhost:6005/websocket/status

## 🔌 WebSocket功能

### 连接和订阅

1. **建立连接**: 连接到 `ws://localhost:6005/ws`
2. **发送订阅消息**:
   ```json
   {
     "type": "subscribe",
     "id": "sub_001",
     "timestamp": "2024-01-01T00:00:00Z",
     "data": {
       "channels": [1001, 1002],
       "data_types": ["T", "S"],
       "interval": 10000
     }
   }
   ```
3. **立即接收数据**: 订阅成功后立即推送一次数据
4. **定时接收数据**: 按照设定的interval间隔推送数据

### 支持的消息类型

#### 客户端发送

- **subscribe**: 订阅数据通道
- **unsubscribe**: 取消订阅
- **control**: 发送控制命令
- **ping**: 心跳检测

#### 服务端推送

- **data_batch**: 批量数据更新
- **alarm**: 告警事件
- **subscribe_ack**: 订阅确认
- **control_ack**: 控制确认
- **pong**: 心跳响应

### 实时数据推送特性

- ✅ 订阅成功后立即推送一次数据
- ✅ 按客户端设定的interval定时推送
- ✅ 支持多通道、多数据类型
- ✅ 自动处理Redis hash类型数据
- ✅ 连接断开自动清理

## 🏭 Edge数据结构支持

项目完全支持Edge数据结构，包括：

- **通信服务 (Comsrv)**: 遥测(T)、遥信(S)、遥控(C)、遥调(A)数据
- **模型服务 (Modsrv)**: 设备模型定义、测量值、控制值
- **告警服务 (Alarmsrv)**: 告警记录、状态管理
- **规则服务 (Rulesrv)**: 规则定义、执行状态

## 🔧 配置说明

### 环境配置文件

- **`config.py`**: 基础配置定义
- **`.env`**: 运行时环境变量
- **`env.development`**: 开发环境配置
- **`env.production`**: 生产环境配置

### 主要配置项

- `REDIS_HOST`: Redis服务器地址
- `REDIS_PORT`: Redis端口 (默认: 6379)
- `JWT_SECRET_KEY`: JWT密钥
- `DEBUG`: 调试模式开关
- `LOG_LEVEL`: 日志级别

## 🧪 测试工具

### WebSocket功能测试

```bash
# 运行完整的WebSocket功能测试
python test_websocket.py
```

### WebSocket客户端测试工具

打开 `websocket_client_test.html` 文件，可以：
- 连接WebSocket服务
- 发送订阅消息
- 查看实时数据推送
- 测试各种消息类型

## 🔧 管理命令

### 本地开发

```bash
# 启动开发环境
./start_websocket.sh

# 运行测试
python test_websocket.py
```

### 工控机管理

```bash
# 查看服务状态
docker ps | grep voltageems-apigateway

# 查看日志
docker logs -f voltageems-apigateway

# 停止服务
docker stop voltageems-apigateway

# 重启服务
docker restart voltageems-apigateway

# 查看健康状态
curl http://localhost:6005/health
```

## 📋 环境要求

### 开发环境

- **Python**: 3.10+
- **Redis**: 运行在指定地址
- **Docker**: 用于构建镜像

### 生产环境（工控机）

- **Docker**: 20.10+
- **架构**: aarch64 (ARM64)
- **Redis**: 运行在localhost:6379
- **网络**: Host网络模式

## 🔍 故障排除

### 常见问题

1. **Redis连接失败**
   - 检查Redis服务状态
   - 验证连接地址和端口
   - 检查网络连通性

2. **WebSocket连接失败**
   - 检查服务是否正常运行
   - 验证端口6005是否可访问
   - 查看防火墙设置

3. **数据推送异常**
   - 检查Redis数据格式（应为hash类型）
   - 验证通道和数据类型是否正确
   - 查看应用日志

### 日志查看

```bash
# 查看应用日志
docker logs voltageems-apigateway

# 查看实时日志
docker logs -f voltageems-apigateway

# 查看最近日志
docker logs --tail 100 voltageems-apigateway
```

## 🎉 部署成功标志

部署成功后，您将看到：

- ✅ Docker镜像加载成功
- ✅ API网关服务运行在端口6005
- ✅ WebSocket连接正常
- ✅ 健康检查通过
- ✅ Redis连接成功
- ✅ 实时数据推送正常

## 📝 版本历史

- **v1.0.0**: 初始版本，基础功能实现
- 支持WebSocket实时数据推送
- 支持Redis hash类型数据读取
- 支持aarch64架构部署
- 优化订阅后立即推送数据

## 📞 联系支持

如有问题或建议，请：

- 查看日志文件排查问题
- 使用测试工具验证功能
- 检查配置文件设置

---

**注意**: 生产环境使用前请修改默认的JWT密钥等敏感配置。