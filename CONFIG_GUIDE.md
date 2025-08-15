# 配置文件使用指南

## 📋 配置文件优先级

配置文件按以下优先级生效（从高到低）：

1. **环境变量** (最高优先级)
2. **`.env` 文件**
3. **`config.py` 中的默认值** (最低优先级)

## 🎯 不同场景的配置

### 🖥️ 本地开发环境

**使用的配置文件**: `env.development` → `.env`

**主要配置**:
```bash
# Redis连接测试服务器
REDIS_HOST=192.168.30.62
REDIS_PORT=6379

# 调试模式
DEBUG=true
LOG_LEVEL=DEBUG
```

**启动方式**:
```bash
./start_websocket.sh
```

### 🏭 打包之前

**修改的文件**: `app/core/config.py`

**建议修改**:
```python
# 确保生产环境的默认配置正确
REDIS_HOST: str = "localhost"  # 生产环境默认本地
DEBUG: bool = False
LOG_LEVEL: str = "INFO"
```

### 🚀 目标工控机

**使用的配置文件**: 
- 如果有`.env`文件：使用`.env`中的配置
- 如果没有`.env`文件：使用`config.py`中的默认值

**主要配置**:
```bash
# Redis连接本地服务
REDIS_HOST=localhost
REDIS_PORT=6379

# 生产模式
DEBUG=false
LOG_LEVEL=INFO
```

**启动方式**:
```bash
cd packages
./load_image.sh
./start.sh
```

## 🔧 配置文件说明

### `config.py`
- **作用**: 定义所有配置项的默认值和类型
- **修改时机**: 打包之前，确保生产环境默认值正确
- **内容**: 应用逻辑相关的配置

### `.env` 文件
- **作用**: 环境特定的配置覆盖
- **优先级**: 高于`config.py`中的默认值
- **内容**: 环境变量，如Redis地址、调试模式等

### `env.development`
- **作用**: 开发环境的配置模板
- **使用**: 本地开发时复制为`.env`
- **内容**: 开发环境特定的配置

### `env.production`
- **作用**: 生产环境的配置模板
- **使用**: 工控机部署时参考
- **内容**: 生产环境特定的配置

## 📝 配置最佳实践

1. **开发环境**: 使用`env.development`，连接测试服务器
2. **打包之前**: 检查`config.py`中的生产环境默认值
3. **工控机部署**: 使用`config.py`中的默认值，或创建`.env`文件覆盖
4. **环境变量**: 最高优先级，适合容器化部署

## 🔍 配置检查

### 检查当前配置
```bash
# 查看Redis连接配置
grep REDIS_HOST .env

# 查看调试模式
grep DEBUG .env

# 查看日志级别
grep LOG_LEVEL .env
```

### 验证配置生效
```bash
# 启动服务后查看日志
docker logs apigateway | grep "Redis连接"

# 检查健康状态
curl http://localhost:6005/health
```
