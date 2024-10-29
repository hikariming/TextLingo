import { Analytics } from "@vercel/analytics/react";
import Head from "next/head";
// 导入 Tailwind CSS
import './/globals.css';

export const metadata = {
  title: {
    default: "Chinese Performance Events - Find Shows in China | Event | Live Information",
    zh: "中国演出活动 - 寻找中国演出 | 活动信息 | 现场信息",
    ja: "中国パフォーマンスイベント - 中国のショーを探す | イベント情報 | ライブ情報"
  },
  description: {
    default: "Discover the latest Chinese performance events and shows. Find information on concerts, theater, and cultural performances , live information across China.",
    zh: "发现最新的中国演出活动和表演。查找中国各地的音乐会、戏剧和文化表演信息，现场信息。",
    ja: "最新の中国パフォーマンスイベントとショーを発見。中国全土のコンサート、劇場、文化公演、ライブ情報を見つけましょう。"
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
    <html lang={lang}>
      <Head>
        <meta name="keywords" content="Chinese performances, events in China, concerts, theater, cultural shows, 中国演出, 中国活动, 音乐会, 戏剧, 文化表演, 中国パフォーマンス, 中国のイベント, コンサート, 劇場, 文化公演" />
        <script type="application/ld+json">
          {`
            {
              "@context": "https://schema.org",
              "@type": "WebSite",
              "name": {
                "@language": "en",
                "@value": "Chinese Performance Events"
              },
              "name": {
                "@language": "zh",
                "@value": "中国演出活动"
              },
              "name": {
                "@language": "ja",
                "@value": "中国パフォーマンスイベント"
              },
              "description": {
                "@language": "en",
                "@value": "Find information on concerts, theater, and cultural performances across China."
              },
              "description": {
                "@language": "zh",
                "@value": "查找中国各地的音乐会、戏剧和文化表演信息。"
              },
              "description": {
                "@language": "ja",
                "@value": "中国全土のコンサート、劇場、文化公演の情報を見つけましょう。"
              }
            }
          `}
        </script>
      </Head>
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
