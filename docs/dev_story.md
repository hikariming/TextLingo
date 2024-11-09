# 10.30

待解决问题：
- [ ✅] navbar的高亮效果在引入i18n后失效。
- [ ✅ ] url、文本导入处理
- [ ✅ ] 加入语法、词汇字段并加入收藏


## win一键包制作

是的，完全可以制作一个免环境安装的独立运行包。以下是具体方案：

1. **MongoDB 便携版**：
使用 MongoDB Portable 版本，打包进软件包中

2. **Python后端打包**：
使用 PyInstaller 将 Flask 应用打包成 exe

3. **Next.js 静态构建**：
使用 `next build` 和 `next export` 生成静态文件

具体实现步骤：

1. 首先创建一个新的打包脚本 `build.bat`:

```batch:build.bat
@echo off
title 打包脚本

:: 打包Python应用
echo 正在打包后端应用...
cd api
pip install pyinstaller
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" app.py

:: 构建Next.js应用
echo 正在构建前端应用...
cd ../web
call npm install
call npm run build

echo 打包完成！
cd ..
```

2. 创建一个新的项目结构用于发布：

```
release/
├── mongodb/              # MongoDB便携版文件夹
│   ├── bin/             # MongoDB可执行文件
│   └── data/            # 数据目录
├── web/                 # Next.js构建后的文件
├── api/                 # Python打包后的exe
├── start.bat           # 启动脚本
└── README.md           # 说明文件
```

3. 修改启动脚本 `start.bat`:

```batch:start.bat
@echo off
title 应用启动器

:: 设置MongoDB路径
set MONGODB_PATH=%~dp0mongodb
set MONGODB_DATA=%MONGODB_PATH%\data
set MONGODB_LOG=%MONGODB_PATH%\log

:: 创建必要的目录
if not exist "%MONGODB_DATA%" mkdir "%MONGODB_DATA%"
if not exist "%MONGODB_LOG%" mkdir "%MONGODB_LOG%"

:: 启动MongoDB
echo 正在启动MongoDB服务...
start /B "MongoDB" "%MONGODB_PATH%\bin\mongod.exe" --dbpath="%MONGODB_DATA%" --logpath="%MONGODB_LOG%\mongodb.log" --port 27017

:: 等待MongoDB启动
timeout /t 5 /nobreak

:: 启动后端服务
echo 正在启动后端服务...
start /B "Backend API" "%~dp0api\app.exe"

:: 启动前端服务
echo 正在启动前端服务...
cd web
start /B "Frontend" npx serve -s out -p 3000

:: 等待服务启动
timeout /t 3 /nobreak

:: 自动打开浏览器
start http://localhost:3000

echo 所有服务已启动！
echo 如需关闭，请直接关闭此窗口。
pause
```

4. 创建停止脚本 `stop.bat`:

```batch:stop.bat
@echo off
:: 结束所有相关进程
taskkill /F /IM mongod.exe
taskkill /F /IM app.exe
taskkill /F /IM node.exe
```

5. 更新 `README.md`:

```markdown:README.md
# 软件使用说明

## 使用步骤
1. 解压所有文件到任意目录
2. 运行 `start.bat` 启动应用
3. 等待浏览器自动打开，访问地址：http://localhost:3000
4. 使用完毕后，运行 `stop.bat` 或直接关闭命令行窗口

## 注意事项
- 首次运行可能需要允许防火墙访问
- 请确保以下端口未被占用：
  - 27017 (MongoDB)
  - 5000 (后端API)
  - 3000 (前端服务)
```

打包准备工作：

1. **MongoDB便携版获取**：
- 下载 MongoDB Community Server zip版本
- 解压后只保留必要的bin目录文件

2. **Python后端打包**：
```bash
# 安装pyinstaller
pip install pyinstaller

# 打包命令
pyinstaller --onefile --hidden-import=flask --hidden-import=flask_cors --hidden-import=pymongo app.py
```

3. **Next.js前端打包**：
```bash
# 安装依赖
npm install

# 构建
npm run build

# 如果需要导出静态文件
next export  # 如果支持的话
```

最后打包步骤：
1. 创建release目录
2. 复制MongoDB便携版到mongodb目录
3. 复制打包后的Python exe到api目录
4. 复制Next.js构建文件到web目录
5. 复制启动脚本和说明文件
6. 使用7-Zip或其他工具打包整个release目录

这样用户就可以直接解压运行，无需安装任何环境了。



MongoDB便携版（Portable Version）指的是 MongoDB Community Server 的 zip 压缩包版本。对于 Windows 系统，我建议使用以下版本：

**MongoDB Community Server 4.4.x zip版本**

原因如下：
1. 4.4.x 版本较为稳定，且对 Windows 7/8/10 都有良好支持
2. 不需要安装为 Windows 服务，可以直接运行
3. 体积相对较小，适合打包分发

下载和准备步骤：

1. 从 MongoDB 官网下载：
```
https://www.mongodb.com/try/download/community
```
- 选择 Version: 4.4.x
- Platform: Windows
- Package: ZIP

2. 解压后只需保留以下核心文件：
````
mongodb/
├── bin/
│   ├── mongod.exe        # 数据库服务器
│   ├── mongo.exe         # 命令行客户端
│   └── *.dll            # 必要的动态链接库
├── data/                 # 数据存储目录（自动创建）
└── log/                  # 日志目录（自动创建）
````

3. 体积优化建议：
- 删除不必要的工具（如 mongodump、mongoexport 等）
- 只保留运行必需的 DLL 文件
- 最终打包体积可以控制在 100MB 左右

这样的便携版本配合之前的启动脚本就可以实现免安装运行了。