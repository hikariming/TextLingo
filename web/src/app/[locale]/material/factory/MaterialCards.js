'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import CreateMaterialModal from './components/CreateMaterialModal'
import { MaterialsAPI } from '@/services/api'
import { ArrowUpTrayIcon, Cog6ToothIcon } from '@heroicons/react/24/outline'

export default function MaterialCards() {
  const t = useTranslations('app')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [factories, setFactories] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchFactories = async () => {
    try {
      setIsLoading(true)
      console.log('Fetching factories...')
      const data = await MaterialsAPI.getAll()
      console.log('API Response:', data)
      setFactories(data)
    } catch (error) {
      console.error('Fetch error:', error)
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
        {[
          // Create Card (Always first)
          <div key="create-card" onClick={() => setIsModalOpen(true)} className="cursor-pointer">
            <div className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center mb-4">
                <div className="text-blue-600 text-xl">+</div>
                <h3 className="text-lg font-medium ml-2 text-black">{t('knowledge.create')}</h3>
              </div>
              <p className="text-black text-sm mb-4">
                {t('knowledge.createDescription')}
              </p>
            </div>
          </div>,

          // Loading or Factory Cards
          ...(isLoading 
            ? [
                <div key="loading" className="col-span-full text-center py-4">
                  Loading...
                </div>
              ]
            : factories.map((factory) => (
                <div key={factory.id} className="block">
                  <Link href={`/${t('locale')}/material/details/${factory.id}`}>
                    <div className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
                      <div className="flex items-center mb-3">
                        <div className="text-blue-600">📁</div>
                        <h3 className="text-lg font-medium ml-2 text-black">{factory.name}</h3>
                      </div>
                      <div className="text-gray-500 text-xs mb-3">
                        {factory.materials?.length || 0} 文档 · 
                        {factory.description || '暂无描述'}
                      </div>
                      <div className="flex gap-2 mt-6 pt-2 border-t">
                        <Link href={`/${t('locale')}/material/create?factoryId=${factory.id}`} className="flex-1">
                          <button className="flex items-center justify-center gap-1 text-xs text-gray-600 hover:text-blue-600 w-full py-0.5">
                            <ArrowUpTrayIcon className="w-3.5 h-3.5" />
                            导入
                          </button>
                        </Link>
                        <div className="w-px bg-gray-200"></div>
                        <button className="flex items-center justify-center gap-1 text-xs text-gray-600 hover:text-blue-600 flex-1 py-0.5">
                          <Cog6ToothIcon className="w-3.5 h-3.5" />
                          管理
                        </button>
                      </div>
                    </div>
                  </Link>
                </div>
              ))
          )
        ]}
      </div>

      <CreateMaterialModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateSuccess}
      />
    </div>
  )
} 