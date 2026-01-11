'use client'

import { useState, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import Navbar from '../../components/navigation/NavbarClient'
import { SettingAPI } from '../../../services/api'
import LLMSettings from './components/LLMSettings'
import VocabularySettings from './components/VocabularySettings'

export default function SettingPage() {
  const t = useTranslations('app.setting')
  const [config, setConfig] = useState({
    llm_api_key: '',
    llm_base_url: '',
    llm_model: '',
    daily_words_target: 20,
    review_interval: 'spaced',
    vocabulary_difficulty: 'medium'
  })

  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [isTesting, setIsTesting] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [activeTab, setActiveTab] = useState('llm')

  // 加载配置
  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const data = await SettingAPI.getConfig()
      setConfig(data)
    } catch (error) {
      setMessage('加载配置失败')
    }
  }

  const updateConfig = (newConfig) => {
    setConfig(newConfig)
    setHasUnsavedChanges(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSaving(true)
    try {
      await SettingAPI.updateConfig(config)
      setMessage('保存成功')
      setHasUnsavedChanges(false)
    } catch (error) {
      setMessage('保存失败')
    }
    setIsSaving(false)
  }

  const handleTest = async () => {
    if (hasUnsavedChanges) {
      setShowConfirmDialog(true)
      return
    }
    await runTest()
  }

  const runTest = async () => {
    setIsTesting(true)
    try {
      const result = await SettingAPI.testLLMConnection()
      setMessage(result.message)
    } catch (error) {
      setMessage(error.message)
    }
    setIsTesting(false)
  }

  return (
    <>
      <Navbar />
      <div className="max-w-2xl mx-auto p-6 mt-16">
        <h1 className="text-2xl font-bold mb-6">{t('title')}</h1>
        
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('llm')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'llm'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {t('llmTab')}
            </button>
            <button
              onClick={() => setActiveTab('vocabulary')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'vocabulary'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {t('vocabularyTab')}
            </button>
          </nav>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-8">
          {activeTab === 'llm' && (
            <LLMSettings 
              config={config}
              onUpdateConfig={updateConfig}
              onTest={handleTest}
              isSaving={isSaving}
              isTesting={isTesting}
              message={message}
            />
          )}

          {activeTab === 'vocabulary' && (
            <VocabularySettings 
              config={config}
              onUpdateConfig={updateConfig}
            />
          )}

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={isSaving}
              className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 disabled:bg-gray-400"
            >
              {isSaving ? t('saving') : t('save')}
            </button>
          </div>
        </form>
      </div>
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-lg max-w-md">
            <h3 className="text-lg font-semibold mb-4">{t('unsavedChangesWarning')}</h3>
            <p className="mb-4">{t('testWithOldConfig')}</p>
            <div className="flex justify-end gap-4">
              <button
                onClick={() => setShowConfirmDialog(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                {t('cancel')}
              </button>
              <button
                onClick={() => {
                  setShowConfirmDialog(false)
                  runTest()
                }}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                {t('continue')}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}