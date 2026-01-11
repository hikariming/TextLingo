'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'

export default function LLMSettings({ config, onUpdateConfig, onTest, isSaving, isTesting, message }) {
  const t = useTranslations('app.setting')

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold mb-4">{t('llmSettings')}</h2>
      
      <div>
        <label className="block text-sm font-medium mb-2">{t('apiKey')}</label>
        <input
          type="text"
          value={config.llm_api_key}
          onChange={(e) => onUpdateConfig({...config, llm_api_key: e.target.value})}
          className="w-full p-2 border rounded-md"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">{t('baseUrl')}</label>
        <div className="flex gap-2">
          <select
            value={config.llm_base_url}
            onChange={(e) => onUpdateConfig({...config, llm_base_url: e.target.value})}
            className="w-2/3 p-2 border rounded-md"
          >
            <option value="">{t('customBaseUrl')}</option>
            <option value="https://api.wlai.vip/v1">https://api.wlai.vip/v1</option>
            <option value="https://api.deepseek.com">https://api.deepseek.com</option>
          </select>
          {!config.llm_base_url && (
            <input
              type="text"
              placeholder={t('baseUrlPlaceholder')}
              value={config.llm_base_url}
              onChange={(e) => onUpdateConfig({...config, llm_base_url: e.target.value})}
              className="w-1/3 p-2 border rounded-md"
            />
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">{t('model')}</label>
        <div className="flex gap-2">
          <select
            value={config.llm_model}
            onChange={(e) => onUpdateConfig({...config, llm_model: e.target.value})}
            className="w-2/3 p-2 border rounded-md"
          >
            <option value="">{t('customModel')}</option>
            <option value="grok-beta">Grok Beta</option>
            <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (20241022)</option>
            <option value="claude-3-5-sonnet-20240620">Claude 3.5 Sonnet (20240620)</option>
            <option value="deepseek-chat">Deepseek Chat</option>
          </select>
          {!config.llm_model && (
            <input
              type="text"
              placeholder={t('modelPlaceholder')}
              value={config.llm_model}
              onChange={(e) => onUpdateConfig({...config, llm_model: e.target.value})}
              className="w-1/3 p-2 border rounded-md"
            />
          )}
        </div>
      </div>

      <div className="flex gap-4">
        <button
          type="button"
          onClick={onTest}
          disabled={isTesting}
          className="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600 disabled:bg-gray-400"
        >
          {isTesting ? t('testing') : t('test')}
        </button>
      </div>

      {message && (
        <div className={`p-3 rounded-md ${
          message.includes('成功') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          {message}
        </div>
      )}
    </div>
  )
}
