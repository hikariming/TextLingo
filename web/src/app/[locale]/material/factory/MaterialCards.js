'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import CreateMaterialModal from './components/CreateMaterialModal'
import { MaterialsAPI } from '@/services/api'

export default function MaterialCards() {
  const t = useTranslations('app')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [factories, setFactories] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchFactories = async () => {
    try {
      setIsLoading(true)
      const data = await MaterialsAPI.getAll()
      console.log(data)
      setFactories(data)
    } catch (error) {
      toast.error(t('knowledge.fetchError'))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchFactories()
  }, [])

  const handleCreateSuccess = async () => {
    toast.success(t('knowledge.createSuccess'))
    await fetchFactories()
    setIsModalOpen(false)
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

        {isLoading ? (
          <div className="col-span-full text-center py-4">Loading...</div>
        ) : (
          factories.map((factory) => (
            <Link key={factory._id} href={`/${t('locale')}/material/details/${factory._id}`}>
              <div className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center mb-4">
                  <div className="text-blue-600">📁</div>
                  <h3 className="text-lg font-medium ml-2 text-black">{factory.name}</h3>
                </div>
                <div className="text-gray-500 text-xs">
                  {factory.materials?.length || 0} 文档 · 
                  {factory.description || '暂无描述'}
                </div>
              </div>
            </Link>
          ))
        )}
      </div>

      <CreateMaterialModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateSuccess}
      />
    </div>
  )
} 