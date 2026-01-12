<div align="center">

<!-- <img src="/docs/img/logo.png" alt="TextLingo Logo" height="140"> -->

# TextLingo Desktop 📕
<p align="center">
  <a href="https://www.python.org" target="_blank"><img src="https://img.shields.io/badge/Tauri-v2-blue.svg" alt="Tauri"></a>
  <a href="https://github.com/hikariming/TextLingo/stargazers" target="_blank"><img src="https://img.shields.io/github/stars/YourUsername/TextLingo.svg" alt="GitHub stars"></a>
</p>

[**English**](/README.md)｜[**中文**](/README_cn.md)

</div>

TextLingo Desktop is an innovative AI-powered foreign language reading and learning tool. It allows you to learn languages using any text content that interests you, transforming boring study into an enjoyable reading experience.

Locally running with Tauri, it offers a fast, privacy-focused, and immersive learning environment.

v0.1 download for chinese

通过网盘分享的文件：0.1.0
链接: https://pan.baidu.com/s/1OGcadEHPohl0QZbRwiK32w?pwd=f2pi 提取码: f2pi 
--来自百度网盘超级会员v8的分享

![TextLingo Main Interface](docs/img/main_page.png)

# Version Information

| Version | Description | Link |
|---------|-------------|------|
| **Desktop Version** | **Recommended** 🖥️ Native performance, local data, supports Mac/Windows/Linux. | [Download Latest Release](https://github.com/hikariming/TextLingo/releases) |
| Web Version |  Convenient online access, no installation required. | [https://textlingo.app](https://textlingo.app) |
| Open Source | 🆓 Fully open source, built with Tauri + React + Rust. | [https://github.com/hikariming/TextLingo](https://github.com/hikariming/TextLingo) |


## Core Features

- 🎯 **Smart Text Import**: One-click import of multiple formats (URL, Word, Markdown, etc.), automatic translation and learning vocabulary generation
- 📖 **Immersive Reading Experience**:
  - Professional reader interface design
  - Real-time language switching
  - Instant word lookup and grammar parsing
- 🔍 **Deep Learning Assistance**:
  - Intelligent word explanations
  - Detailed grammar explanations (supports Chinese-Japanese-English translation)
  - Context understanding support
  - Pronunciation guidance and correction

# Use Cases 🎬

- 📚 Lyrics Learning: Learn Japanese through music lyrics 🎵, convenient for singing along at concerts
- 📰 News Reading: Read Japanese and English news (The Economist, idol reports, etc.), stay updated with current events
- 📝 Vocabulary Memorization: Memorize words through lyrics, news, and other texts
- 📖 Grammar Practice: Practice grammar through reading foreign language materials

## Coming Soon
- 📝 Text Intelligent Dialogue: Supports highlight learning and real-time Q&A
- 📚 Personalized Exercise System: Targeted word and grammar practice

# How to Run

### Development

1. **Prerequisites**: Ensure you have Node.js and Rust installed.
2. **Install Dependencies**:
   ```bash
   cd textlingo-desktop
   npm install
   ```
3. **Run in Development Mode**:
   ```bash
   npm run tauri dev
   ```

For more details, refer to [Development Documentation](docs/HowToRun_en.md).

## Troubleshooting
### macOS: "App is damaged and can't be opened"
If you encounter this error, it is due to macOS Gatekeeper. Please run the following command in Terminal:
```bash
sudo xattr -r -d com.apple.quarantine /Applications/TextLingo\ Desktop.app
```

## Supported Languages
- 🇨🇳 Chinese (Simplified)
- 🇺🇸 English
- 🇯🇵 Japanese
  - Supports kana notation
  - Automatic grammar analysis
- More languages coming soon, or submit PR or issue


## kou的作品
日区 AI 导航站 aitoolsjapan 是一个日区 AI 导航站，在这里你可以发现各类与人工智能相关的日本地区的工具和资源，帮助你快速找到所需的 AI 服务和应用。

dify 的使用学习分享站 usedify 是一个专注于 dify 的使用学习分享站。在这里，你可以学习到 dify 相关的使用技巧、经验分享以及各种实用的案例，助力你更好地掌握和运用 dify 工具。

基于感兴趣文本学习外语的站 textlingo 是一个基于自己感兴趣文本学习外语的站。通过该网站，你能够利用自己感兴趣的文本内容作为学习材料，以更有趣和高效的方式提升外语水平。

## Current Version

Development version v0.1.4
Please check the running documentation for how to run the development version

# Introduction to my other Interesting Websites

## Japanese AI Navigation Station
[aitoolsjapan](https://aitoolsjapan.com/) is a Japanese AI navigation website. Here, you can discover a wide range of AI-related tools and resources from Japan. It serves as a convenient hub to quickly find the AI services and applications you need, whether you're exploring cutting - edge AI technologies or looking for practical AI - powered tools.

## dify Usage and Learning Sharing Platform
[usedify](https://usedify.app/) is a specialized platform dedicated to the usage and learning of dify. On this site, you can access a wealth of valuable content, including dify usage tips, hands - on experience sharing, and practical case studies. Whether you're a beginner getting started with dify or an experienced user aiming to master advanced features, usedify provides the knowledge and insights to help you make the most of the dify tool.

## Foreign Language Learning Site Based on Personalized Texts
[textlingo](https://textlingo.app/) is a platform that enables foreign language learning based on texts that interest you. Instead of traditional language learning materials, it allows you to leverage your personal interests, such as favorite novels, articles, or blogs, as study resources. This unique approach makes language learning more engaging and effective, helping you improve your language proficiency while exploring topics you love.
