# 正式版本

使用Docker一键部署（TBD）

# 开发版本



## 环境要求
- Python 3.8+
- Node.js 16+
- MongoDB 4.0+

## 一、后端部署

### 1. 安装依赖
```bash
cd api
pip install -r requirements.txt
```

### 2. 配置文件
将配置模板复制为正式配置：
```bash
cp config.example.yml config.yml
```

编辑 `config.yml`：
```yaml
mongodb:
  uri: "mongodb://username:password@localhost:27017/dbname?authSource=admin"
  # 修改为你的 MongoDB 连接信息

secret_key: "your-secret-key-here" 
# 设置随机字符串作为密钥

llm_api_key: "your-openai-api-key-here"
# 填入你的 API key

llm_base_url: "https://api.wlai.vip/v1"  
# 官方API地址：https://api.openai.com/v1
# 第三方API地址根据供应商提供

llm_model: "claude-3-5-sonnet-20241022"  
# 可选模型：gpt-4-turbo-preview、gpt-3.5-turbo 等
```

### 3. 启动后端
```bash
cd api
python app.py
```

默认启动在 `http://localhost:5000`

## 二、前端部署

### 1. 安装依赖
```bash
cd web

# 使用 npm 安装
npm install

# 或使用 pnpm（推荐，速度更快）
pnpm install

# 或使用 cnpm（国内网络较差时使用）
cnpm install
```

### 2. 开发环境运行
```bash
npm run dev
```
默认启动在 `http://localhost:3000`

### 3. 生产环境构建
```bash
npm run build
```
构建产物在 `dist` 目录下

## 三、注意事项

1. MongoDB 相关：
   - 确保 MongoDB 服务已启动
   - 正确配置数据库用户名和密码
   - 确保数据库端口可访问

2. API 相关：
   - 确保 API Key 有效且有足够额度
   - 如使用第三方 API，确保服务稳定可用

3. 网络相关：
   - 如遇跨域问题，检查后端 CORS 配置
   - 确保前后端端口未被占用

4. 生产环境部署：
   - 建议使用 nginx 做前端静态资源服务器
   - 后端建议使用 gunicorn 或 uwsgi 做 WSGI 服务器
   - 建议配置 SSL 证书启用 HTTPS

## 四、常见问题排查

1. 前端无法连接后端：
   - 检查后端服务是否正常运行
   - 检查前端配置的 API 地址是否正确
   - 检查网络连接和防火墙设置

2. MongoDB 连接失败：
   - 检查 MongoDB 服务状态
   - 验证连接字符串格式
   - 确认用户权限配置

3. API 调用失败：
   - 检查 API Key 配置
   - 确认模型名称是否正确
   - 查看 API 余额是否充足





