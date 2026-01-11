# 使用Python 3.9作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制requirements.txt
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY . .

# 暴露端口
EXPOSE 3001

# 修改启动命令
CMD ["python", "app.py"]