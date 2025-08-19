# API网关部署包

## 📁 文件说明

- `voltageems-apigateway-*.tar.gz` - 预构建的Docker镜像文件
- `start.sh` - 工控机启动脚本
- `load_image.sh` - 镜像加载脚本
- `verify_deployment.sh` - 部署验证脚本
- `build_image.sh` - 镜像构建脚本（开发机使用）
- `README.md` - 部署说明文档

## 🚀 快速部署

### 1. 传输文件到工控机
将以下文件传输到工控机：
- `voltageems-apigateway-*.tar.gz` (镜像文件)
- `load_image.sh` (镜像加载脚本)
- `start.sh` (服务启动脚本)
- `verify_deployment.sh` (部署验证脚本)
- `README.md` (部署说明文档)

### 2. 加载Docker镜像
```bash
chmod +x *.sh
./load_image.sh
```
**说明**: 脚本会自动为加载的镜像创建`latest`标签

### 3. 启动服务
```bash
./start.sh
```
**说明**: 脚本会智能选择可用的镜像版本并：
- 优先使用`latest`标签
- 其次选择版本号最高的镜像
- 最后使用任意可用镜像
- 自动创建外部配置目录：`/extp/config`
- 首次运行时自动创建管理员用户

### 4. 验证部署
```bash
./verify_deployment.sh
```
**说明**: 验证脚本会检查：
- Docker和容器状态
- 端口监听情况
- 健康检查接口
- 配置和日志目录
- 认证API功能
- Redis连接状态

## 🔧 管理命令

```bash
# 查看服务状态
docker ps | grep voltageems-apigateway

# 查看日志
docker logs voltageems-apigateway

# 停止服务
docker stop voltageems-apigateway

# 重启服务
docker restart voltageems-apigateway
```

## 📱 服务访问

- API网关: http://localhost:6005
- WebSocket: ws://localhost:6005/ws
- 健康检查: http://localhost:6005/health

## ⚠️ 注意事项

1. 确保Redis服务运行在localhost:6379
2. 确保6005端口未被占用
3. 使用host网络模式，直接访问宿主机网络
4. 目录挂载：
   - 日志目录：`/extp/logs` → `/app/logs`
   - 配置目录：`/extp/config` → `/app/config`
5. 数据库文件将存储在：`/extp/config/voltageems.db`
6. 镜像名称：voltageems-apigateway
7. 容器名称：voltageems-apigateway

## 🔐 默认管理员账户

首次启动时会自动创建管理员账户：
- **用户名**: `admin`
- **密码**: `admin123`
- **邮箱**: `admin@voltageems.com`
- **角色**: 管理员

⚠️ **安全提醒**: 请在首次登录后立即修改默认密码！

## 📊 数据持久化

配置和数据文件存储在工控机的 `/extp/` 目录下：
```
/extp/
├── config/
│   └── voltageems.db    # SQLite数据库文件
└── logs/
    └── apigateway.log   # 应用日志文件
```

**环境自动检测**：系统会自动检测运行环境
- 🐳 **容器环境**：数据库存储在 `/app/config/voltageems.db`（映射到 `/extp/config/`）
- 💻 **开发环境**：数据库存储在 `app/config/voltageems.db`（项目目录内）

## 🔄 版本升级

1. 构建新版本镜像
2. 传输新的 `.tar.gz` 文件到工控机
3. 运行 `./load_image.sh` 加载新镜像
4. 运行 `./start.sh` 重启服务

**注意**: 升级不会影响已存在的用户数据和配置文件。
