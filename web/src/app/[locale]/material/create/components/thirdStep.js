'use client'
import { useTranslations } from 'next-intl'

export default function ThirdStep({ onPrev, targetLanguage, enableDeepExplanation }) {
  const t = useTranslations('app.material.create.complete')
  
  // 语言显示映射
  const languageMap = {
    'zh-CN': '简体中文',
    'en': 'English',
    'ja': '日本語'
  }

  return (
    <div className="p-6">
      {/* 标题部分 */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold">{t('title')}</h2>
        <p className="text-gray-600 mt-2">{t('subtitle')}</p>
      </div>

      {/* 素材库信息 */}
      <div className="bg-gray-50 p-6 rounded-lg mb-8">
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">{t('libraryName')}</label>
          <input 
            type="text" 
            className="w-full p-2 border rounded-md"
            defaultValue="14317738_20241024..."
            disabled
          />
        </div>

        {/* 处理状态信息 */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-gray-700">{t('translationTask')}</span>
            <span className="text-green-600">{t('submitted')}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-700">{t('targetLanguage')}</span>
            <span className="text-gray-600">{languageMap[targetLanguage]}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-700">{t('deepExplanation')}</span>
            <span className="text-gray-600">{enableDeepExplanation ? t('enabled') : t('disabled')}</span>
          </div>
        </div>
      </div>

      {/* 下一步提示 */}
      <div className="bg-blue-50 p-6 rounded-lg mb-8">
        <h3 className="text-lg font-medium mb-2">{t('processingTitle')}</h3>
        <p className="text-gray-600">
          {t('processingDescription', {
            language: languageMap[targetLanguage],
            explanation: enableDeepExplanation ? t('withExplanation') : ''
          })}
        </p>
      </div>

      {/* 按钮区域 */}
      <div className="flex justify-between">
        <button
          onClick={onPrev}
          className="px-4 py-2 border rounded-md text-gray-600 hover:bg-gray-50"
        >
          {t('previous')}
        </button>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          onClick={() => window.location.href = '/'}
        >
          {t('goToDocument')}
        </button>
      </div>
    </div>
  )
}
