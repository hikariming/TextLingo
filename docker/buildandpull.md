要为不同架构构建和发布 Docker 镜像，你可以使用 `buildx` 来创建多平台镜像。以下是具体步骤：

1. 首先创建一个新的 builder 实例：
```bash
docker buildx create --name mybuilder --use
```

2. 然后使用以下命令构建并推送多平台镜像：
```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t yourdockerhubusername/textlingo-web:0.20 \
  --push \
  .
```

### 说明：
- `linux/amd64`: 适用于 Windows/Intel Mac
- `linux/arm64`: 适用于 M1/M2 Mac (Apple Silicon)
- `yourdockerhubusername`: 替换为你的 Docker Hub 用户名
- `--push`: 直接推送到 Docker Hub

### 在推送之前，确保：
1. 已经登录到 Docker Hub：
```bash
docker login
```

2. 如果要单独测试某个平台的构建：
```bash
# 仅构建 ARM 版本
docker buildx build --platform linux/arm64 -t yourdockerhubusername/textlingo-web:0.20-arm64 .

# 仅构建 AMD64 版本
docker buildx build --platform linux/amd64 -t yourdockerhubusername/textlingo-web:0.20-amd64 .
```

注意：Docker Hub 会自动处理不同架构的镜像，用户在拉取时会自动获取适合其系统架构的版本。