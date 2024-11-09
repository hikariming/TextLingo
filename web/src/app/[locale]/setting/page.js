'use client'

import { useState, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import Navbar from '../../components/navigation/NavbarClient'
import { SettingAPI } from '../../../services/api'

export default function SettingPage() {
  const t = useTranslations('app.setting')
  const [config, setConfig] = useState({
    llm_api_key: '',
    llm_base_url: '',
    llm_model: ''
  })

  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [isTesting, setIsTesting] = useState(false)

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

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSaving(true)
    try {
      await SettingAPI.updateConfig(config)
      setMessage('保存成功')
    } catch (error) {
      setMessage('保存失败')
    }
    setIsSaving(false)
  }

  const handleTest = async () => {
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
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">{t('apiKey')}</label>
            <input
              type="text"
              value={config.llm_api_key}
              onChange={(e) => setConfig({...config, llm_api_key: e.target.value})}
              className="w-full p-2 border rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">{t('baseUrl')}</label>
            <input
              type="text"
              value={config.llm_base_url}
              onChange={(e) => setConfig({...config, llm_base_url: e.target.value})}
              className="w-full p-2 border rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">{t('model')}</label>
            <div className="flex gap-2">
              <select
                value={config.llm_model}
                onChange={(e) => setConfig({...config, llm_model: e.target.value})}
                className="w-2/3 p-2 border rounded-md"
              >
                <option value="">自定义输入</option>
                <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (20241022)</option>
                <option value="claude-3-5-sonnet-20240620">Claude 3.5 Sonnet (20240620)</option>
                <option value="deepseek-chat">Deepseek Chat</option>
              </select>
              {!config.llm_model && (
                <input
                  type="text"
                  placeholder="输入模型名称"
                  value={config.llm_model}
                  onChange={(e) => setConfig({...config, llm_model: e.target.value})}
                  className="w-1/3 p-2 border rounded-md"
                />
              )}
            </div>
          </div>

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={isSaving}
              className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 disabled:bg-gray-400"
            >
              {isSaving ? t('saving') : t('save')}
            </button>

            <button
              type="button"
              onClick={handleTest}
              disabled={isTesting}
              className="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600 disabled:bg-gray-400"
            >
              {isTesting ? '测试中...' : '测试连接'}
            </button>
          </div>

          {message && (
            <div className={`p-3 rounded-md ${
              message.includes('成功') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              {message}
            </div>
          )}
        </form>
      </div>
    </>
  )
}