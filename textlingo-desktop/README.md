# TextLingo Desktop (Independent Edition)

An AI-powered desktop application for reading, translating, and analyzing articles. Designed as a **Local-First, Independent Application** that connects directly to LLM providers.

## Architecture & Privacy

- **Fully Independent**: Reads, manages, and analyzes articles entirely on your local machine using a high-performance **Rust Backend**.
- **Direct AI Connection**: Connects directly to AI providers (OpenAI, DeepSeek, etc.) without any intermediate servers. Your requests go straight from your computer to the AI API.
- **Privacy First**: Your API keys, articles, and reading history stored locally (`~/Library/Application Support/` or equivalent). No account required.
- **Zero-Dependency**: Does not require a separate Node.js backend server for core features.

## Features

- **Article Management**: Create, edit, and organize articles locally
- **AI Translation**: Translate articles to your target language
- **AI Explanation (Rust-Native)**:
    - Get sentence-by-sentence explanations
    - Detailed vocabulary and grammar analysis
    - **No middleware required** - powered by local Rust logic
- **Article Analysis**: Summary, key points, and difficulty assessment
- **Multiple AI Providers**: Support for OpenAI, OpenRouter, DeepSeek, and Google (Gemini)


## Tech Stack

- **Frontend**: React 19, TypeScript, Tailwind CSS
- **Backend**: Rust (Tauri v2)
- **Build**: Vite
- **UI Components**: Custom components inspired by shadcn/ui

## Project Structure

```
textlingo-desktop/
├── src/                          # React frontend
│   ├── components/
│   │   ├── ui/                  # Reusable UI components
│   │   ├── features/            # Feature-specific components
│   │   │   ├── ArticleList.tsx  # Article list view
│   │   │   ├── ArticleReader.tsx # Article detail view
│   │   │   ├── NewArticleDialog.tsx # Create article
│   │   │   └── SettingsDialog.tsx # API key configuration
│   │   └── layout/              # Layout components
│   ├── lib/
│   │   ├── tauri.ts            # Tauri command types
│   │   └── utils.ts            # Utility functions
│   ├── App.tsx                 # Main app component
│   └── main.tsx                # Entry point
├── src-tauri/                   # Rust backend
│   ├── src/
│   │   ├── lib.rs              # Tauri app setup
│   │   ├── main.rs             # Entry point
│   │   ├── commands.rs         # Tauri commands
│   │   ├── ai_service.rs       # AI API integration
│   │   ├── storage.rs          # Local file storage
│   │   └── types.rs            # Type definitions
│   ├── Cargo.toml              # Rust dependencies
│   └── tauri.conf.json         # Tauri configuration
└── package.json                # Node dependencies
```

## Getting Started

### Prerequisites

- Node.js 18+
- Rust 1.70+
- Tauri CLI

### Installation

```bash
cd textlingo-desktop
npm install
```

### Development

```bash
npm run tauri dev
```

### Build

```bash
npm run tauri build
```

Build artifacts will be in `src-tauri/target/release/bundle/`

## Usage

1. **Configure API Key**: Click "Settings" and enter your API key
2. **Create Article**: Click "New Article" and paste your content
3. **Translate**: Open an article and click "Translate"
4. **Analyze**: Switch to the "Analysis" tab and select analysis type

## Supported AI Providers

| Provider | Models |
|----------|--------|
| OpenAI | GPT-4o, GPT-4o Mini, GPT-4 Turbo, GPT-3.5 Turbo |
| OpenRouter | GPT-4o, Claude 3 Haiku, Gemini Pro 1.5 |
| DeepSeek | DeepSeek Chat, DeepSeek Coder |
| Google | Gemini 2.0 Flash, Gemini 1.5 Pro/Flash |

## Configuration

API keys and settings are stored locally in:
- **macOS**: `~/Library/Application Support/com.textlingo.desktop/`
- **Linux**: `~/.config/textlingo-desktop/`
- **Windows**: `%APPDATA%\com.textlingo.desktop\`

## License

MIT
