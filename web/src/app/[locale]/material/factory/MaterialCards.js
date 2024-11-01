'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { useState } from 'react'
import CreateMaterialModal from './components/CreateMaterialModal'

export default function KnowledgeCards() {
  const t = useTranslations('app')
  const [isModalOpen, setIsModalOpen] = useState(false)

  // 现有素材库数据示例
  const existingKnowledgeBases = [
    {
      title: 'Copy of 易智平台及易智助手',
      count: '1 文档',
      size: '13 千字符',
      usage: '0 知识'
    },
    // ... 其他素材库数据
  ]

  const handleCreateSuccess = () => {
    // 这里可以添加刷新素材库列表的逻辑
  }

  return (
    <div className="bg-slate-100 min-h-screen">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4">
        {/* 新建素材库卡片 */}
        <div onClick={() => setIsModalOpen(true)} className="cursor-pointer">
          <div className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center mb-4">
              <div className="text-blue-600 text-xl">+</div>
              <h3 className="text-lg font-medium ml-2 text-black">{t('knowledge.create')}</h3>
            </div>
            <p className="text-black text-sm mb-4">
              {t('knowledge.createDescription')}
            </p>
          </div>
        </div>

        {/* 现有素材库卡片 */}
        {existingKnowledgeBases.map((kb, index) => (
          <Link key={index} href={`/${t('locale')}/material/details`}>
            <div className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center mb-4">
                <div className="text-blue-600">📁</div>
                <h3 className="text-lg font-medium ml-2 text-black">{kb.title}</h3>
              </div>
              <div className="text-gray-500 text-xs">
                {kb.count} · {kb.size} · {kb.usage}
              </div>
            </div>
          </Link>
        ))}
      </div>

      <CreateMaterialModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateSuccess}
      />
    </div>
  )
} 