#!/bin/bash

# 创建完整部署包脚本
# 将所有必要的文件打包成一个部署包

echo "📦 创建API网关部署包..."

# 检查必要文件是否存在
REQUIRED_FILES=(
    "voltageems-apigateway-*.tar.gz"
    "start.sh"
    "load_image.sh"
    "verify_deployment.sh"
    "README.md"
)

echo "🔍 检查必要文件..."
for pattern in "${REQUIRED_FILES[@]}"; do
    if ! ls $pattern >/dev/null 2>&1; then
        echo "❌ 缺少文件: $pattern"
        exit 1
    fi
done
echo "✅ 所有必要文件都存在"

# 获取版本号
IMAGE_FILE=$(ls voltageems-apigateway-*.tar.gz | head -1)
VERSION=$(echo $IMAGE_FILE | sed 's/voltageems-apigateway-\(.*\)\.tar\.gz/\1/')

if [ -z "$VERSION" ]; then
    VERSION="unknown"
fi

PACKAGE_NAME="voltageems-apigateway-deployment-${VERSION}"
TEMP_DIR="/tmp/${PACKAGE_NAME}"

echo "📋 部署包信息:"
echo "   版本: $VERSION"
echo "   包名: ${PACKAGE_NAME}.tar.gz"

# 创建临时目录
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# 复制文件到临时目录
echo "📂 复制文件..."
cp voltageems-apigateway-*.tar.gz "$TEMP_DIR/"
cp start.sh "$TEMP_DIR/"
cp load_image.sh "$TEMP_DIR/"
cp verify_deployment.sh "$TEMP_DIR/"
cp README.md "$TEMP_DIR/"

# 确保脚本有执行权限
chmod +x "$TEMP_DIR"/*.sh

# 创建部署包
echo "🗜️  创建压缩包..."
cd /tmp
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"

# 移动到原目录
ORIGINAL_DIR=$(pwd)
cd - >/dev/null
cp "/tmp/${PACKAGE_NAME}.tar.gz" "./"

# 清理临时目录
rm -rf "$TEMP_DIR" "/tmp/${PACKAGE_NAME}.tar.gz"

echo "✅ 部署包创建成功！"
echo "📁 文件位置: ${PACKAGE_NAME}.tar.gz"
echo "📊 文件大小: $(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1)"
echo ""
echo "🚀 部署说明:"
echo "1. 将 ${PACKAGE_NAME}.tar.gz 传输到工控机"
echo "2. 在工控机上解压: tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "3. 进入目录: cd ${PACKAGE_NAME}"
echo "4. 按照 README.md 说明进行部署"
echo ""
echo "🎉 打包完成！"
