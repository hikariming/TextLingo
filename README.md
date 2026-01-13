<div align="center">

<!-- <img src="/docs/img/logo.png" alt="TextLingo Logo" height="140"> -->

# TextLingo Desktop 📕

**Open Source Language Learning Tool | Free Alternative to Language Reactor & Duolingo**

<p align="center">
  <a href="https://tauri.app" target="_blank"><img src="https://img.shields.io/badge/Tauri-v2-blue.svg" alt="Tauri"></a>
  <a href="https://github.com/hikariming/TextLingo/stargazers" target="_blank"><img src="https://img.shields.io/github/stars/hikariming/TextLingo.svg" alt="GitHub stars"></a>
  <a href="https://github.com/hikariming/TextLingo/blob/main/LICENSE" target="_blank"><img src="https://img.shields.io/badge/license-Apache%202.0-green.svg" alt="License"></a>
</p>

[**English**](/README.md)｜[**中文**](/README_cn.md)｜[**日本語**](/README_ja.md)

</div>

## What is TextLingo?

TextLingo Desktop is an **open-source, AI-powered language learning application** that transforms any content you're interested in into an immersive learning experience. Unlike traditional language learning apps, TextLingo lets you learn from **real-world content** — song lyrics, news articles, blog posts, or any text that sparks your interest.

Built with **Tauri + React + Rust**, it runs locally on your machine for **fast performance and complete privacy**.

> 🎯 **Perfect for**: Japanese learners, English learners, polyglots, and anyone who wants to learn languages through content they actually enjoy!

![TextLingo Main Interface](docs/img/main_page.png)

## Why TextLingo?

| Feature | TextLingo | Traditional Apps |
|---------|-----------|------------------|
| 📖 Learn from any content | ✅ Import URLs, docs, lyrics | ❌ Fixed curriculum |
| 🔒 Privacy-focused | ✅ 100% local processing | ❌ Cloud-dependent |
| 🆓 Free & open source | ✅ Apache 2.0 License | ❌ Subscription-based |
| 🌍 100+ languages supported | ✅ Learning & transcription | ❌ Limited languages |
| 🖥️ Native desktop performance | ✅ Tauri + Rust | ❌ Web-based lag |
| 🤖 AI-powered explanations | ✅ Smart context analysis | ❌ Limited feedback |

## Download

| Version | Description | Link |
|---------|-------------|------|
| **Desktop** | **Recommended** 🖥️ Native performance, local data, Mac/Windows/Linux | [Download Latest Release](https://github.com/hikariming/TextLingo/releases) |
| Web | Convenient online access, no installation required | [https://textlingo.app](https://textlingo.app) |
| Source Code | 🆓 Fully open source, MIT License | [GitHub Repository](https://github.com/hikariming/TextLingo) |

**中国用户下载**: [百度网盘](https://pan.baidu.com/s/1OGcadEHPohl0QZbRwiK32w?pwd=f2pi) (提取码: f2pi)

## Core Features

- 🎯 **Smart Text Import** - One-click import from URLs, Word, Markdown, and more with automatic translation and vocabulary extraction
- 📖 **Immersive Reading Mode**
  - Professional reader interface
  - Real-time language switching
  - Instant word lookup and grammar parsing
- 🔍 **AI Learning Assistant**
  - Intelligent word explanations in context
  - Detailed grammar breakdowns (Chinese-Japanese-English)
  - Pronunciation guidance and correction
- 📝 **Personalized Learning** - Highlight and ask questions about any text in real-time

## Use Cases 🎬

- 🎵 **Learn Japanese through Song Lyrics** - Master pronunciation for your favorite J-Pop songs and concerts
- 📰 **Read News in Foreign Languages** - The Economist, NHK News, and more with instant translations
- 📚 **Study with Real Content** - Import any article, blog post, or document that interests you
- 🎬 **Anime Learning** - Understand your favorite Japanese anime with transcription support

## Coming Soon

- 📝 Interactive text dialogue with AI Q&A
- 📚 Personalized vocabulary and grammar exercise system
- 🎥 YouTube video learning support

## Getting Started

### Prerequisites
- Node.js (v18+)
- Rust

### Development Setup

1. **Clone and download binaries**:
   ```bash
   git clone https://github.com/hikariming/TextLingo.git
   cd TextLingo
   chmod +x script/download_binaries.sh
   ./script/download_binaries.sh
   ```

2. **Install dependencies**:
   ```bash
   cd textlingo-desktop
   npm install
   ```

3. **Run in development mode**:
   ```bash
   npm run tauri dev
   ```

For more details, see [Development Documentation](docs/HowToRun_en.md).

## Troubleshooting

### macOS: "App is damaged and can't be opened"
This is due to macOS Gatekeeper. Run in Terminal:
```bash
sudo xattr -r -d com.apple.quarantine /Applications/TextLingo\ Desktop.app
```

## Supported Languages

**100+ languages supported** for learning and transcription, including:

- 🇯🇵 Japanese (with furigana support and auto grammar analysis)
- 🇺🇸 English
- 🇨🇳 Chinese (Simplified & Traditional)
- 🇰🇷 Korean
- 🇫🇷 French
- 🇩🇪 German
- 🇪🇸 Spanish
- 🇮🇹 Italian
- 🇵🇹 Portuguese
- And many more...

PRs welcome for additional language support!

## Tech Stack

- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend**: Tauri + Rust
- **AI**: OpenAI-compatible API integration

## Contributing

We welcome contributions! Please feel free to submit PRs or open issues.

## Current Version

**v0.1.4** (Development)

## Related Projects by the Author

### Japanese AI Navigation Station
[aitoolsjapan](https://aitoolsjapan.com/) is a Japanese AI navigation website. Here, you can discover a wide range of AI-related tools and resources from Japan. It serves as a convenient hub to quickly find the AI services and applications you need, whether you're exploring cutting-edge AI technologies or looking for practical AI-powered tools.

### Dify Usage and Learning Sharing Platform
[usedify](https://usedify.app/) is a specialized platform dedicated to the usage and learning of Dify. On this site, you can access a wealth of valuable content, including Dify usage tips, hands-on experience sharing, and practical case studies. Whether you're a beginner getting started with Dify or an experienced user aiming to master advanced features, usedify provides the knowledge and insights to help you make the most of the Dify tool.

### Foreign Language Learning Site Based on Personalized Texts
[textlingo](https://textlingo.app/) is a platform that enables foreign language learning based on texts that interest you. Instead of traditional language learning materials, it allows you to leverage your personal interests, such as favorite novels, articles, or blogs, as study resources. This unique approach makes language learning more engaging and effective, helping you improve your language proficiency while exploring topics you love.

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details

---

<div align="center">

**⭐ Star this repo if TextLingo helps you learn languages! ⭐**

[Report Bug](https://github.com/hikariming/TextLingo/issues) · [Request Feature](https://github.com/hikariming/TextLingo/issues) · [Join Discussion](https://github.com/hikariming/TextLingo/discussions)

</div>
