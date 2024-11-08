'use client'

import { useState, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import Navbar from '../../components/navigation/NavbarClient'

export default function SettingPage() {
  const t = useTranslations('app.setting')
  const [config, setConfig] = useState({
    llm_api_key: '',
    llm_base_url: '',
    llm_model: ''
  })

  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState('')

  // 加载配置
  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/config')
      const data = await response.json()
      setConfig(data)
    } catch (error) {
      setMessage('加载配置失败')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSaving(true)
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      })
      if (response.ok) {
        setMessage('保存成功')
      } else {
        setMessage('保存失败')
      }
    } catch (error) {
      setMessage('保存失败')
    }
    setIsSaving(false)
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
            <select
              value={config.llm_model}
              onChange={(e) => setConfig({...config, llm_model: e.target.value})}
              className="w-full p-2 border rounded-md"
            >
              <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
            </select>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSaving}
              className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 disabled:bg-gray-400"
            >
              {isSaving ? t('saving') : t('save')}
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