import { Analytics } from "@vercel/analytics/react";
import { NextIntlClientProvider } from 'next-intl';
import ThemeProvider from '../components/ThemeProvider';
import '../globals.css';

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

export default async function RootLayout({ children, params }) {
  const locale = params.locale;
  
  let messages;
  try {
    console.log('Loading messages for locale:', locale);
    messages = (await import(`../../../content/${locale}.json`)).default;
    console.log('Messages loaded successfully');
  } catch (error) {
    console.error('Error loading messages:', error);
    console.log('Falling back to English locale');
    messages = (await import(`../../../content/en.json`)).default;
  }

  if (!messages) {
    console.error('No messages loaded, using empty messages object');
    messages = {};
  }

  return (
    <html lang={locale} className="light">
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider>
            {children}
            <Analytics />
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
 