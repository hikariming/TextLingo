# TextLingo Desktop 📕
<p align="center">
  <a href="https://www.python.org" target="_blank"><img src="https://img.shields.io/badge/Tauri-v2-blue.svg" alt="Tauri"></a>
  <a href="https://github.com/hikariming/TextLingo/stargazers" target="_blank"><img src="https://img.shields.io/github/stars/YourUsername/TextLingo.svg" alt="GitHub stars"></a>
</p>

[**English**](/README.md)｜[**中文**](/README_cn.md)

</div>

TextLingo Desktop 是一款创新的 AI 驱动的外语阅读与学习工具。它让您可以使用任何感兴趣的文本内容来学习外语，将枯燥的语言学习转变为充满乐趣的阅读体验。

基于 Tauri 开发，提供原生、快速、注重隐私的沉浸式学习环境。

![TextLingo 主界面](docs/img/main_page.png)

## 核心特性

- 🎯 **智能文本导入**：支持多种格式（URL、Word、Markdown等）的一键导入，自动翻译并生成学习词汇
- 📖 **沉浸式阅读体验**：
  - 专业的阅读器界面设计
  - 多语言实时切换
  - 实时查词与语法解析
- 🔍 **深度学习辅助**：
  - 智能单词解释
  - 详细语法讲解（支持中日英三语互译）
  - 上下文理解支持
  - 发音指导与纠正

# 使用场景🎬

- 📚 歌词学习：学习日语、音乐歌曲🎵，方便演唱会跟唱
- 📰 新闻阅读：阅读日文、英文新闻（经济学人、偶像报道等），了解时事新闻
- 📝 单词背诵：通过歌词、新闻等文本背诵单词
- 📖 语法练习：通过阅读外语材料来练习语法


# 版本说明

| 版本 | 说明 | 链接 |
|---------|-------------|------|
| **桌面版** | **推荐** 🖥️ 原生性能，本地数据，支持 Mac/Windows/Linux。 | [下载最新版本](https://github.com/hikariming/TextLingo/releases) |
| 网页版 |  最方便，无需安装。 | [https://textlingo.app](https://textlingo.app) |
| 开源版 | 🆓 完全开源，基于 Tauri + React + Rust 构建。 | [https://github.com/hikariming/TextLingo](https://github.com/hikariming/TextLingo) |


# 运行方式

### 开发环境

1. **前置条件**：确保已安装 Node.js 和 Rust 环境。
2. **安装依赖**：
   ```bash
   cd textlingo-desktop
   npm install
   ```
3. **启动开发模式**：
   ```bash
   npm run tauri dev
   ```

更多详情请参考 [开发文档](docs/HowToRun_cn.md)。


## 常见问题
### macOS: "应用已损坏，打不开"
如果遇到此错误，是因为 macOS Gatekeeper 安全机制。请在终端运行以下命令：
```bash
sudo xattr -r -d com.apple.quarantine /Applications/TextLingo\ Desktop.app
```

## 支持语言
- 🇨🇳 中文 (简体)
- 🇺🇸 English
- 🇯🇵 日本語
  - 支持假名标注
  - 自动语法分析
- 更多语言敬请期待，或提交pr或issue

## 当前版本

开发版v0.1.0
运行开发版方式请查看运行文档