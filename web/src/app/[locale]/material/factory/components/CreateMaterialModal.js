'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'

export default function CreateMaterialModal({ isOpen, onClose, onSubmit }) {
  const t = useTranslations('app')
  const [formData, setFormData] = useState({
    name: '',
    description: ''
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const response = await fetch('/api/materials-factory', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: formData.name,
          description: formData.description,
          // user_id 应该从认证系统获取
        })
      })
      
      if (response.ok) {
        onSubmit()
        onClose()
      }
    } catch (error) {
      console.error('Error creating material:', error)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96">
        <h2 className="text-xl font-bold mb-4">{t('knowledge.create')}</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">{t('knowledge.name')}</label>
            <input
              type="text"
              className="w-full border rounded-md p-2"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({...prev, name: e.target.value}))}
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">{t('knowledge.description')}</label>
            <textarea
              className="w-full border rounded-md p-2"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({...prev, description: e.target.value}))}
              rows="3"
              required
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              {t('common.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}