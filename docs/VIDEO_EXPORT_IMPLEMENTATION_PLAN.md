# 视频字幕导出功能实现规划

> **文档版本**: v1.0  
> **创建日期**: 2026-01-18  
> **状态**: 规划中

## 📋 功能概述

本文档详细规划了 TextLingo/OpenKoto 应用中**带字幕视频导出**功能的实现方案。

### 目标功能

| 功能 | 描述 |
|------|------|
| **原文字幕视频导出** | 将原文字幕硬编码/软编码到视频中导出 |
| **译文字幕视频导出** | 将翻译字幕硬编码/软编码到视频中导出 |
| **双语字幕视频导出** | 同时显示原文和译文（上下双行布局） |

---

## 🏗️ 技术架构

### 现有基础设施

```
textlingo-desktop/
├── src-tauri/
│   ├── binaries/
│   │   ├── ffmpeg-aarch64-apple-darwin      ✅ 已有
│   │   ├── ffmpeg-x86_64-apple-darwin       ✅ 已有
│   │   ├── ffmpeg-x86_64-pc-windows-msvc.exe ✅ 已有
│   │   └── ffmpeg-x86_64-unknown-linux-gnu  ✅ 已有
│   └── src/
│       ├── subtitle_extraction.rs           ✅ 已有字幕提取
│       └── video_export.rs                  🆕 需新增
└── src/
    └── components/features/
        ├── VideoSubtitlePlayer.tsx          ✅ 已有字幕导出 SRT
        └── VideoExportDialog.tsx            🆕 需新增
```

### 技术选型

| 技术 | 选择 | 理由 |
|------|------|------|
| 视频处理 | FFmpeg (已集成) | 功能强大，跨平台，已打包为 sidecar |
| 字幕格式 | SRT / ASS | SRT 简单通用，ASS 支持双语样式 |
| 后端语言 | Rust (Tauri) | 与现有架构一致 |
| 前端框架 | React + TypeScript | 与现有架构一致 |

---

## 📐 字幕嵌入方式对比

### 软字幕 (Soft Subtitles)

将字幕作为独立轨道嵌入视频容器，用户可选择开关。

```bash
# FFmpeg 命令示例
ffmpeg -i input.mp4 -i subtitle.srt -c copy -c:s mov_text output.mp4
```

| 优点 | 缺点 |
|------|------|
| ✅ 导出速度快（不需重编码） | ❌ 部分播放器不支持 |
| ✅ 用户可开关字幕 | ❌ 移动端兼容性差 |
| ✅ 可嵌入多语言轨道 | ❌ 分享到社交平台时可能不显示 |

### 硬字幕 (Hardcoded Subtitles)

将字幕永久烧录到视频画面中。

```bash
# FFmpeg 命令示例 - SRT 字幕
ffmpeg -i input.mp4 -vf "subtitles=subtitle.srt:force_style='FontSize=24,FontName=Noto Sans CJK SC'" -c:a copy output.mp4

# FFmpeg 命令示例 - ASS 字幕（支持更丰富样式）
ffmpeg -i input.mp4 -vf "ass=subtitle.ass" -c:a copy output.mp4
```

| 优点 | 缺点 |
|------|------|
| ✅ 所有播放器都能显示 | ❌ 需要重新编码视频（耗时） |
| ✅ 社交平台分享完美兼容 | ❌ 字幕不可关闭 |
| ✅ 样式可精细控制 | ❌ 导出文件可能变大 |

### 推荐策略

**默认提供两种选项让用户选择：**
1. 快速导出（软字幕）- 适合本地观看
2. 兼容导出（硬字幕）- 适合分享到社交平台

---

## 🎨 双语字幕布局方案

### ASS 字幕格式

ASS (Advanced SubStation Alpha) 格式支持多种样式，可实现双语上下布局。

```ass
[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Original,Noto Sans CJK SC,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,60,1
Style: Translation,Noto Sans CJK SC,40,&H0000FFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Original,,0,0,0,,こんにちは、世界
Dialogue: 0,0:00:01.00,0:00:05.00,Translation,,0,0,0,,你好，世界
```

### 样式说明

| 样式属性 | Original (原文) | Translation (译文) |
|----------|-----------------|-------------------|
| 字体大小 | 48px | 40px |
| 颜色 | 白色 (`&H00FFFFFF`) | 黄色 (`&H0000FFFF`) |
| 位置 | 偏上 (MarginV=60) | 偏下 (MarginV=10) |
| Alignment | 2 (底部居中) | 2 (底部居中) |

### 视觉效果

```
┌─────────────────────────────────────┐
│                                     │
│          [视频画面区域]               │
│                                     │
│                                     │
│        こんにちは、世界  ← 原文 (白色)  │
│          你好，世界    ← 译文 (黄色)   │
└─────────────────────────────────────┘
```

---

## 🔧 实现阶段规划

### 阶段 1：基础设施 (工作量: ~4h)

#### 1.1 新建 Rust 模块

**文件**: `src-tauri/src/video_export.rs`

```rust
// 视频导出模块
// 
// 功能：
// 1. 生成 SRT/ASS 临时字幕文件
// 2. 调用 FFmpeg 进行字幕嵌入
// 3. 支持软字幕和硬字幕两种模式

use std::path::{Path, PathBuf};
use tauri::AppHandle;
use crate::types::ArticleSegment;

/// 字幕类型
pub enum SubtitleType {
    Original,     // 仅原文
    Translated,   // 仅译文
    Bilingual,    // 双语
}

/// 嵌入模式
pub enum EmbedMode {
    Soft,   // 软字幕（嵌入轨道）
    Hard,   // 硬字幕（烧录画面）
}

/// 导出配置
pub struct ExportConfig {
    pub subtitle_type: SubtitleType,
    pub embed_mode: EmbedMode,
    pub font_size: u32,
    pub font_name: String,
}

/// 导出进度事件
pub struct ExportProgress {
    pub percent: f32,
    pub stage: String,
    pub message: String,
}

/// 视频导出主函数
pub async fn export_video_with_subtitles(
    app: AppHandle,
    video_path: &Path,
    segments: Vec<ArticleSegment>,
    output_path: &Path,
    config: ExportConfig,
    event_id: &str,
) -> Result<PathBuf, String> {
    // TODO: 实现
    todo!()
}
```

#### 1.2 注册 Tauri 命令

**文件**: `src-tauri/src/commands.rs` (新增)

```rust
#[tauri::command]
pub async fn export_video_with_subtitles_cmd(
    app: AppHandle,
    video_path: String,
    article_id: String,
    output_path: String,
    subtitle_type: String,  // "original" | "translated" | "bilingual"
    embed_mode: String,     // "soft" | "hard"
    event_id: String,
) -> Result<String, String> {
    // TODO: 实现
    todo!()
}
```

#### 1.3 注册模块

**文件**: `src-tauri/src/lib.rs` (修改)

```rust
mod video_export;  // 新增

// 在 invoke_handler 中添加
commands::export_video_with_subtitles_cmd,
```

---

### 阶段 2：SRT 字幕生成 (工作量: ~2h)

#### 2.1 SRT 生成器

**文件**: `src-tauri/src/video_export.rs` (追加)

```rust
/// 生成 SRT 字幕文件
fn generate_srt_file(
    segments: &[ArticleSegment],
    subtitle_type: &SubtitleType,
    output_path: &Path,
) -> Result<PathBuf, String> {
    let mut content = String::new();
    
    for (index, seg) in segments.iter().enumerate() {
        let start = format_srt_time(seg.start_time.unwrap_or(0.0));
        let end = format_srt_time(seg.end_time.unwrap_or(0.0));
        
        content.push_str(&format!("{}\n", index + 1));
        content.push_str(&format!("{} --> {}\n", start, end));
        
        match subtitle_type {
            SubtitleType::Original => {
                content.push_str(&format!("{}\n", seg.text));
            }
            SubtitleType::Translated => {
                content.push_str(&format!("{}\n", seg.translation.as_deref().unwrap_or("")));
            }
            SubtitleType::Bilingual => {
                content.push_str(&format!("{}\n", seg.text));
                content.push_str(&format!("{}\n", seg.translation.as_deref().unwrap_or("")));
            }
        }
        content.push('\n');
    }
    
    std::fs::write(output_path, content)
        .map_err(|e| format!("写入 SRT 文件失败: {}", e))?;
    
    Ok(output_path.to_path_buf())
}

/// 格式化 SRT 时间 (HH:MM:SS,mmm)
fn format_srt_time(seconds: f64) -> String {
    let hrs = (seconds / 3600.0) as u32;
    let mins = ((seconds % 3600.0) / 60.0) as u32;
    let secs = (seconds % 60.0) as u32;
    let ms = ((seconds % 1.0) * 1000.0) as u32;
    format!("{:02}:{:02}:{:02},{:03}", hrs, mins, secs, ms)
}
```

---

### 阶段 3：ASS 字幕生成 (工作量: ~4h)

#### 3.1 ASS 生成器（双语专用）

**文件**: `src-tauri/src/video_export.rs` (追加)

```rust
/// 生成 ASS 字幕文件（支持双语上下布局）
fn generate_ass_file(
    segments: &[ArticleSegment],
    config: &ExportConfig,
    output_path: &Path,
) -> Result<PathBuf, String> {
    let mut content = String::new();
    
    // Script Info
    content.push_str("[Script Info]\n");
    content.push_str("ScriptType: v4.00+\n");
    content.push_str("PlayResX: 1920\n");
    content.push_str("PlayResY: 1080\n");
    content.push_str("Timer: 100.0000\n\n");
    
    // Styles
    content.push_str("[V4+ Styles]\n");
    content.push_str("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n");
    
    // 原文样式 - 白色，位置偏上
    content.push_str(&format!(
        "Style: Original,{},{},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,60,1\n",
        config.font_name,
        config.font_size
    ));
    
    // 译文样式 - 黄色，位置偏下
    content.push_str(&format!(
        "Style: Translation,{},{},&H0000FFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1\n",
        config.font_name,
        (config.font_size as f32 * 0.85) as u32
    ));
    content.push('\n');
    
    // Events
    content.push_str("[Events]\n");
    content.push_str("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n");
    
    for seg in segments {
        let start = format_ass_time(seg.start_time.unwrap_or(0.0));
        let end = format_ass_time(seg.end_time.unwrap_or(0.0));
        
        // 原文行
        content.push_str(&format!(
            "Dialogue: 0,{},{},Original,,0,0,0,,{}\n",
            start, end, seg.text
        ));
        
        // 译文行
        if let Some(ref translation) = seg.translation {
            content.push_str(&format!(
                "Dialogue: 0,{},{},Translation,,0,0,0,,{}\n",
                start, end, translation
            ));
        }
    }
    
    std::fs::write(output_path, content)
        .map_err(|e| format!("写入 ASS 文件失败: {}", e))?;
    
    Ok(output_path.to_path_buf())
}

/// 格式化 ASS 时间 (H:MM:SS.cc)
fn format_ass_time(seconds: f64) -> String {
    let hrs = (seconds / 3600.0) as u32;
    let mins = ((seconds % 3600.0) / 60.0) as u32;
    let secs = (seconds % 60.0) as u32;
    let cs = ((seconds % 1.0) * 100.0) as u32;  // 厘秒
    format!("{}:{:02}:{:02}.{:02}", hrs, mins, secs, cs)
}
```

---

### 阶段 4：FFmpeg 集成 (工作量: ~6h)

#### 4.1 软字幕嵌入

```rust
/// 软字幕嵌入（快速，不需重编码）
async fn embed_soft_subtitles(
    app: &AppHandle,
    video_path: &Path,
    subtitle_path: &Path,
    output_path: &Path,
    event_id: &str,
) -> Result<(), String> {
    let output = app.shell()
        .sidecar("ffmpeg")
        .map_err(|e| format!("无法创建 FFmpeg sidecar: {}", e))?
        .args([
            "-i", video_path.to_str().unwrap(),
            "-i", subtitle_path.to_str().unwrap(),
            "-c", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=und",
            "-y",
            output_path.to_str().unwrap(),
        ])
        .output()
        .await
        .map_err(|e| format!("FFmpeg 执行失败: {}", e))?;
    
    if !output.status.success() {
        return Err(format!("FFmpeg 错误: {}", String::from_utf8_lossy(&output.stderr)));
    }
    
    Ok(())
}
```

#### 4.2 硬字幕烧录

```rust
/// 硬字幕烧录（需要重编码）
async fn burn_hard_subtitles(
    app: &AppHandle,
    video_path: &Path,
    subtitle_path: &Path,
    output_path: &Path,
    event_id: &str,
) -> Result<(), String> {
    let subtitle_ext = subtitle_path.extension()
        .and_then(|e| e.to_str())
        .unwrap_or("srt");
    
    let filter = if subtitle_ext == "ass" {
        format!("ass={}", subtitle_path.to_str().unwrap().replace("\\", "/").replace(":", "\\:"))
    } else {
        format!(
            "subtitles={}:force_style='FontSize=24,FontName=Noto Sans CJK SC'",
            subtitle_path.to_str().unwrap().replace("\\", "/").replace(":", "\\:")
        )
    };
    
    // 使用 spawn 和进度监控
    let (mut rx, child) = app.shell()
        .sidecar("ffmpeg")
        .map_err(|e| format!("无法创建 FFmpeg sidecar: {}", e))?
        .args([
            "-i", video_path.to_str().unwrap(),
            "-vf", &filter,
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-y",
            "-progress", "pipe:1",  // 输出进度信息
            output_path.to_str().unwrap(),
        ])
        .spawn()
        .map_err(|e| format!("FFmpeg 执行失败: {}", e))?;
    
    // 监控进度并发送事件
    // TODO: 解析 FFmpeg 进度输出并通过 app.emit() 发送进度
    
    Ok(())
}
```

#### 4.3 进度解析

```rust
/// 解析 FFmpeg 进度输出
fn parse_ffmpeg_progress(line: &str) -> Option<f32> {
    // FFmpeg progress 输出格式:
    // out_time_ms=12345678
    // 解析出时间，与总时长对比计算百分比
    
    if line.starts_with("out_time_ms=") {
        let time_ms: i64 = line
            .trim_start_matches("out_time_ms=")
            .parse()
            .ok()?;
        // 需要知道视频总时长才能计算百分比
        // 这里返回毫秒数，由调用者计算百分比
        Some(time_ms as f32 / 1000.0)
    } else {
        None
    }
}
```

---

### 阶段 5：前端 UI (工作量: ~6h)

#### 5.1 导出对话框组件

**文件**: `src/components/features/VideoExportDialog.tsx`

```tsx
import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { RadioGroup, RadioGroupItem } from "../ui/RadioGroup";
import { Label } from "../ui/Label";
import { Progress } from "../ui/Progress";
import { useTranslation } from "react-i18next";
import { invoke } from "@tauri-apps/api/core";
import { save } from "@tauri-apps/plugin-dialog";
import { listen } from "@tauri-apps/api/event";

interface VideoExportDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    videoPath: string;
    articleId: string;
    articleTitle: string;
    hasTranslations: boolean;
}

type SubtitleType = "original" | "translated" | "bilingual";
type EmbedMode = "soft" | "hard";

export function VideoExportDialog({
    open,
    onOpenChange,
    videoPath,
    articleId,
    articleTitle,
    hasTranslations,
}: VideoExportDialogProps) {
    const { t } = useTranslation();
    const [subtitleType, setSubtitleType] = useState<SubtitleType>("original");
    const [embedMode, setEmbedMode] = useState<EmbedMode>("soft");
    const [isExporting, setIsExporting] = useState(false);
    const [progress, setProgress] = useState(0);
    const [statusMessage, setStatusMessage] = useState("");

    const handleExport = async () => {
        try {
            // 选择保存路径
            const outputPath = await save({
                defaultPath: `${articleTitle.replace(/[/\\?%*:|"<>]/g, "-")}_subtitled.mp4`,
                filters: [{ name: "MP4 Video", extensions: ["mp4"] }],
            });

            if (!outputPath) return;

            setIsExporting(true);
            setProgress(0);
            setStatusMessage(t("videoExport.preparing"));

            const eventId = `export_${Date.now()}`;

            // 监听进度事件
            const unlisten = await listen<{ percent: number; message: string }>(
                `export_progress_${eventId}`,
                (event) => {
                    setProgress(event.payload.percent);
                    setStatusMessage(event.payload.message);
                }
            );

            try {
                await invoke("export_video_with_subtitles_cmd", {
                    videoPath,
                    articleId,
                    outputPath,
                    subtitleType,
                    embedMode,
                    eventId,
                });

                setStatusMessage(t("videoExport.completed"));
                setProgress(100);
                
                // 延迟关闭
                setTimeout(() => {
                    onOpenChange(false);
                    setIsExporting(false);
                    setProgress(0);
                }, 1500);
            } finally {
                unlisten();
            }
        } catch (error) {
            console.error("Export failed:", error);
            setStatusMessage(t("videoExport.failed"));
            setIsExporting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>{t("videoExport.title")}</DialogTitle>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {/* 字幕类型选择 */}
                    <div className="space-y-3">
                        <Label className="text-sm font-medium">
                            {t("videoExport.subtitleType")}
                        </Label>
                        <RadioGroup
                            value={subtitleType}
                            onValueChange={(v) => setSubtitleType(v as SubtitleType)}
                            className="gap-3"
                        >
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value="original" id="original" />
                                <Label htmlFor="original">
                                    {t("videoExport.originalOnly")}
                                </Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem
                                    value="translated"
                                    id="translated"
                                    disabled={!hasTranslations}
                                />
                                <Label
                                    htmlFor="translated"
                                    className={!hasTranslations ? "opacity-50" : ""}
                                >
                                    {t("videoExport.translatedOnly")}
                                    {!hasTranslations && ` (${t("videoExport.noTranslations")})`}
                                </Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem
                                    value="bilingual"
                                    id="bilingual"
                                    disabled={!hasTranslations}
                                />
                                <Label
                                    htmlFor="bilingual"
                                    className={!hasTranslations ? "opacity-50" : ""}
                                >
                                    {t("videoExport.bilingual")}
                                    {!hasTranslations && ` (${t("videoExport.noTranslations")})`}
                                </Label>
                            </div>
                        </RadioGroup>
                    </div>

                    {/* 嵌入模式选择 */}
                    <div className="space-y-3">
                        <Label className="text-sm font-medium">
                            {t("videoExport.embedMode")}
                        </Label>
                        <RadioGroup
                            value={embedMode}
                            onValueChange={(v) => setEmbedMode(v as EmbedMode)}
                            className="gap-3"
                        >
                            <div className="flex items-start space-x-2">
                                <RadioGroupItem value="soft" id="soft" className="mt-1" />
                                <div>
                                    <Label htmlFor="soft" className="font-medium">
                                        {t("videoExport.softSubtitle")}
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        {t("videoExport.softSubtitleDesc")}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-2">
                                <RadioGroupItem value="hard" id="hard" className="mt-1" />
                                <div>
                                    <Label htmlFor="hard" className="font-medium">
                                        {t("videoExport.hardSubtitle")}
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        {t("videoExport.hardSubtitleDesc")}
                                    </p>
                                </div>
                            </div>
                        </RadioGroup>
                    </div>

                    {/* 进度显示 */}
                    {isExporting && (
                        <div className="space-y-2">
                            <Progress value={progress} className="h-2" />
                            <p className="text-sm text-muted-foreground text-center">
                                {statusMessage} ({Math.round(progress)}%)
                            </p>
                        </div>
                    )}
                </div>

                {/* 操作按钮 */}
                <div className="flex justify-end gap-3">
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={isExporting}
                    >
                        {t("common.cancel")}
                    </Button>
                    <Button onClick={handleExport} disabled={isExporting}>
                        {isExporting ? t("videoExport.exporting") : t("videoExport.export")}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
```

#### 5.2 国际化文本

**文件**: `src/i18n/locales/zh.json` (追加)

```json
{
  "videoExport": {
    "title": "导出带字幕视频",
    "subtitleType": "字幕类型",
    "originalOnly": "仅原文字幕",
    "translatedOnly": "仅译文字幕",
    "bilingual": "双语字幕（原文+译文）",
    "noTranslations": "需先翻译",
    "embedMode": "嵌入方式",
    "softSubtitle": "软字幕（快速）",
    "softSubtitleDesc": "字幕作为独立轨道，可开关。适合本地观看。",
    "hardSubtitle": "硬字幕（兼容）",
    "hardSubtitleDesc": "字幕烧录到画面，不可关闭。适合分享到社交平台。",
    "export": "导出视频",
    "exporting": "导出中...",
    "preparing": "准备中...",
    "processing": "处理中...",
    "completed": "导出完成！",
    "failed": "导出失败，请重试"
  }
}
```

---

### 阶段 6：字体处理 (工作量: ~4h)

#### 6.1 字体打包策略

**推荐方案**: 使用 Google Noto CJK 字体

```
src-tauri/
└── resources/
    └── fonts/
        └── NotoSansCJKsc-Regular.otf  (~15MB)
```

#### 6.2 字体路径获取

```rust
/// 获取字体文件路径
fn get_font_path(app: &AppHandle) -> Result<PathBuf, String> {
    // 优先使用打包的字体
    let resource_path = app.path()
        .resource_dir()
        .map_err(|e| format!("获取资源目录失败: {}", e))?
        .join("fonts")
        .join("NotoSansCJKsc-Regular.otf");
    
    if resource_path.exists() {
        return Ok(resource_path);
    }
    
    // 回退到系统字体
    #[cfg(target_os = "macos")]
    {
        let system_font = PathBuf::from("/System/Library/Fonts/PingFang.ttc");
        if system_font.exists() {
            return Ok(system_font);
        }
    }
    
    #[cfg(target_os = "windows")]
    {
        let system_font = PathBuf::from("C:\\Windows\\Fonts\\msyh.ttc");
        if system_font.exists() {
            return Ok(system_font);
        }
    }
    
    Err("未找到可用的 CJK 字体".to_string())
}
```

---

## 📊 工作量汇总

| 阶段 | 内容 | 工作量 | 累计 |
|------|------|--------|------|
| 阶段 1 | 基础设施搭建 | 4h | 4h |
| 阶段 2 | SRT 字幕生成 | 2h | 6h |
| 阶段 3 | ASS 字幕生成 | 4h | 10h |
| 阶段 4 | FFmpeg 集成 | 6h | 16h |
| 阶段 5 | 前端 UI | 6h | 22h |
| 阶段 6 | 字体处理 | 4h | 26h |
| 测试 & 调试 | 全流程测试 | 4h | **30h** |

**总计**: 约 **30 小时** 工作量

---

## ⚠️ 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| FFmpeg 在某些平台执行失败 | 中 | 高 | 添加详细错误日志，提供手动安装指引 |
| 长视频导出耗时过长 | 高 | 中 | 使用较快的编码预设，显示进度预估 |
| CJK 字体显示异常 | 中 | 高 | 打包可靠的 Noto CJK 字体 |
| ASS 样式在某些播放器显示不一致 | 低 | 低 | 使用最通用的样式设置 |

---

## 🧪 测试清单

### 功能测试

- [ ] 原文软字幕导出
- [ ] 原文硬字幕导出
- [ ] 译文软字幕导出
- [ ] 译文硬字幕导出
- [ ] 双语软字幕导出
- [ ] 双语硬字幕导出

### 平台测试

- [ ] macOS (Apple Silicon)
- [ ] macOS (Intel)
- [ ] Windows 10/11
- [ ] Linux (Ubuntu)

### 边界情况

- [ ] 长视频 (> 1 小时)
- [ ] 空字幕段落
- [ ] 特殊字符 (emoji, 生僻字)
- [ ] 视频分辨率适配

---

## 📚 参考资料

- [FFmpeg Subtitle Documentation](https://trac.ffmpeg.org/wiki/HowToBurnSubtitlesIntoVideo)
- [ASS Subtitle Format Specification](https://github.com/libass/libass)
- [Tauri Sidecar Documentation](https://v2.tauri.app/develop/sidecar/)
- [Noto CJK Fonts](https://github.com/notofonts/noto-cjk)

---

*文档完*
