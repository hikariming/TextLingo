import { notFound } from "next/navigation";
import { getRequestConfig } from 'next-intl/server';

const locales: string[] = ['en', 'jp', 'zh'];

export const metadata = {
  title: {
    en: "Chinese Performance Events - Find Shows in China | Event Information",
    zh: "中国演出活动 - 寻找中国演出 | 活动信息",
    jp: "中国パフォーマンスイベント - 中国のショーを探す | イベント情報"
  },
  description: {
    en: "Discover the latest Chinese performance events and shows. Find information on concerts, theater, and cultural performances across China.",
    zh: "发现最新的中国演出活动和表演。查找中国各地的音乐会、戏剧和文化表演信息。",
    jp: "最新の中国パフォーマンスイベントとショーを発見。中国全土のコンサート、劇場、文化公演の情報を見つけましょう。"
  },
  alternates: {
    languages: {
      'en': '/en',
      'zh': '/zh',
      'jp': '/jp'
    },
  },
};

export default getRequestConfig(async ({ locale }) => {
  if (!locales.includes(locale as any)) notFound();

  return {
    messages: (await import(`../content/${locale}.json`)).default,
    metadata: metadata[locale as keyof typeof metadata] || metadata.en
  };
});

export function getAlternateLinks(currentPath: string) {
  return locales.map(locale => ({
    hrefLang: locale,
    href: `/${locale}${currentPath}`
  }));
}