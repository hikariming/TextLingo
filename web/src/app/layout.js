import { Analytics } from "@vercel/analytics/react";
import Head from "next/head";
import ThemeProvider from './components/ThemeProvider';
// 导入 Tailwind CSS
import './/globals.css';

export const metadata = {
  title: {
    default: "TextLingo - Read, Translate & Learn Foreign Text Materials | Global Learning Platform",
    zh: "TextLingo - 阅读、翻译、学习海外文本素材 | 全球学习平台",
    ja: "TextLingo - 海外テキスト文本の読解、翻訳、学習 | グローバル学習プラットフォーム"
  },
  description: {
    default: "Explore and learn from diverse text materials worldwide. Enhance your language skills through interactive reading, translation, and learning experiences.",
    zh: "探索和学习来自世界各地的多样化文本素材。通过互动阅读、翻译和学习体验提升您的语言能力。",
    ja: "世界中の多様なテキスト文本を探索し、学習。インタラクティブな読解、翻訳、学習体験で語学力を向上させましょう。"
  },
  alternates: {
    languages: {
      'en-US': '/en',
      'zh-CN': '/zh',
      'ja-JP': '/jp'
    },
  },
};

export default function RootLayout({ children, params: { lang } }) {
  return (
    <html lang={lang} className="light">
      <Head>
        <meta name="keywords" content="Chinese performances, events in China, concerts, theater, cultural shows, 中国演出, 中国活动, 音乐会, 戏剧, 文化表演, 中国パフォーマンス, 中国のイベント, コンサート, 劇場, 文化公演" />
        <script type="application/ld+json">
          {`
            {
              "@context": "https://schema.org",
              "@type": "WebSite",
              "name": {
                "@language": "en",
                "@value": "TextLingo"
              },
              "name": {
                "@language": "zh",
                "@value": "TextLingo"
              },
              "name": {
                "@language": "ja",
                "@value": "TextLingo"
              },
              "description": {
                "@language": "en",
                "@value": "Learn from global text materials through reading, translation and interactive learning."
              },
              "description": {
                "@language": "zh",
                "@value": "通过阅读、翻译和互动学习来学习全球文本素材。"
              },
              "description": {
                "@language": "ja",
                "@value": "読解、翻訳、インタラクティブな学習で世界のテキスト文本を学びましょう。"
              }
            }
          `}
        </script>
      </Head>
      <body>
        <ThemeProvider>
          {children}
          <Analytics />
        </ThemeProvider>
      </body>
    </html>
  );
}
