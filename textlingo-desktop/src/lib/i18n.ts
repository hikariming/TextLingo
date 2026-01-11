import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "../locales/en.json";
import zh from "../locales/zh.json";
import ja from "../locales/ja.json";

// Get saved language preference from localStorage
const getSavedLanguage = (): string => {
  try {
    const saved = localStorage.getItem("textlingo-language");
    if (saved && ["en", "zh", "ja"].includes(saved)) {
      return saved;
    }
  } catch {
    // Ignore localStorage errors
  }
  // Detect from browser
  const browserLang = navigator.language.split("-")[0];
  if (["zh", "ja"].includes(browserLang)) {
    return browserLang;
  }
  return "en";
};

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      zh: { translation: zh },
      ja: { translation: ja },
    },
    lng: getSavedLanguage(),
    fallbackLng: "en",
    interpolation: {
      escapeValue: false,
    },
  });

// Save language preference when it changes
i18n.on("languageChanged", (lng) => {
  try {
    localStorage.setItem("textlingo-language", lng);
  } catch {
    // Ignore localStorage errors
  }
});

export default i18n;
