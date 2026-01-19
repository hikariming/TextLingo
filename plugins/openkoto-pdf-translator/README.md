# OpenKoto PDF Translator Plugin

基于 [PDFMathTranslate](https://github.com/Byaidu/PDFMathTranslate) 的 PDF 翻译插件，专为 OpenKoto 定制。

## 功能

- 📊 保留 PDF 原始排版（公式、图表、表格）
- 🌐 支持多语言翻译
- 📄 生成双语对照 PDF
- 🔗 与 OpenKoto 主程序模型配置集成

## 支持的翻译服务

继承自 OpenKoto 主程序配置：
- OpenAI / OpenRouter / DeepSeek
- SiliconFlow / 302.AI
- Google AI Studio (Gemini)
- Ollama / LM Studio (本地)

## 安装（开发模式）

```bash
cd plugins/openkoto-pdf-translator
pip install -e .
```

## 使用

### 命令行

```bash
# 使用 OpenKoto 配置
export OPENKOTO_PROVIDER=openai
export OPENKOTO_API_KEY=your-api-key
export OPENKOTO_MODEL=gpt-4o-mini

openkoto-pdf-translate input.pdf -lo zh
```

### Python API

```python
from openkoto_pdf_translator.openkoto_translator import OpenKotoTranslator
from openkoto_pdf_translator.high_level import translate

# 使用 OpenKoto 翻译器
translate(
    ["input.pdf"],
    output="./output",
    lang_out="zh",
    service="openkoto"  # 使用 OpenKoto 配置
)
```

### 配置文件

创建 `~/.openkoto/translator_config.json`:

```json
{
  "provider": "openai",
  "api_key": "your-api-key",
  "model": "gpt-4o-mini",
  "base_url": null
}
```

## 构建独立可执行文件

```bash
pip install pyinstaller
python build.py
```

输出在 `dist/` 目录，可分发给用户直接使用。

## GitHub Actions 自动构建

推送 `pdf-translator-v*` 标签会自动触发多平台构建：
- Windows x64
- macOS Intel / Apple Silicon
- Linux x64

---

*基于 PDFMathTranslate 项目修改，遵循 AGPL-3.0 许可证*
