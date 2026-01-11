'use client'

import { BookOpenIcon, ArrowLeftIcon } from '@heroicons/react/24/outline'
import { useEffect, useState } from 'react'
import { MaterialsAPI } from '@/services/api'

export default function ReadingMaterials({ 
  selectedMaterial, 
  onMaterialSelect 
}) {
  const [materials, setMaterials] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 直接获取材料列表
  useEffect(() => {
    const fetchMaterials = async () => {
      try {
        setLoading(true)
        const response = await MaterialsAPI.getMaterialsByFactory(window.location.pathname.split('/').pop())
        setMaterials(response.materials || [])
      } catch (err) {
        console.error('Failed to fetch materials:', err)
        setError('Failed to load materials')
      } finally {
        setLoading(false)
      }
    }

    fetchMaterials()
  }, [])

  if (loading) {
    return (
      <nav className="w-64 border-r border-neutral-200 bg-slate-50 p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-slate-200 rounded"></div>
            <div className="h-4 bg-slate-200 rounded"></div>
            <div className="h-4 bg-slate-200 rounded"></div>
          </div>
        </div>
      </nav>
    )
  }

  if (error) {
    return (
      <nav className="w-64 border-r border-neutral-200 bg-slate-50 p-4">
        <div className="text-red-500 text-sm">
          <h2 className="font-semibold mb-2">Error</h2>
          <p>{error}</p>
        </div>
      </nav>
    )
  }

  return (
    <nav className="w-64 border-r border-neutral-200 bg-slate-50 p-4 flex flex-col h-full">
      <div className="flex-grow">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Reading Materials</h2>
        
        {materials.length === 0 ? (
          <p className="text-gray-500 text-sm">No materials available，没有可用的文档，请先上传文档</p>
        ) : (
          <ul className="space-y-2">
            {materials.map((material) => (
              <li key={material._id}>
                <button
                  className={`w-full flex items-center px-4 py-2 rounded-lg text-left transition-colors
                    ${selectedMaterial === material._id 
                      ? 'bg-white text-blue-600 shadow-sm' 
                      : 'text-gray-900 hover:bg-gray-100'
                    }`}
                  onClick={() => onMaterialSelect(material._id)}
                  title={material.title}
                >
                  <BookOpenIcon className={`flex-shrink-0 mr-2 h-4 w-4 ${
                    selectedMaterial === material._id ? 'text-blue-600' : 'text-gray-500'
                  }`} />
                  <span className="truncate">
                    {material.title}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <button
        onClick={() => window.history.back()}
        className="w-full flex items-center px-4 py-2 rounded-lg text-white bg-blue-600 hover:bg-blue-700 transition-colors"
      >
        <ArrowLeftIcon className="flex-shrink-0 mr-2 h-4 w-4" />
        <span>返回上一页</span>
      </button>
    </nav>
  )
}
