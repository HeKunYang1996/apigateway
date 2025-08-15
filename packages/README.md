# API网关部署包

## 📁 文件说明

- `voltageems-apigateway-*.tar.gz` - 预构建的Docker镜像文件
- `start.sh` - 工控机启动脚本
- `load_image.sh` - 镜像加载脚本
- `build_image.sh` - 镜像构建脚本（开发机使用）

## 🚀 快速部署

### 1. 加载Docker镜像
```bash
chmod +x *.sh
./load_image.sh
```
**说明**: 脚本会自动为加载的镜像创建`latest`标签

### 2. 启动服务
```bash
./start.sh
```
**说明**: 脚本会智能选择可用的镜像版本：
- 优先使用`latest`标签
- 其次选择版本号最高的镜像
- 最后使用任意可用镜像

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
4. 日志目录：/extp/logs
5. 镜像名称：voltageems-apigateway
6. 容器名称：voltageems-apigateway
