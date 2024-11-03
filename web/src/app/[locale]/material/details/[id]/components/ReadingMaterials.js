'use client'

import { BookOpenIcon } from '@heroicons/react/24/outline'
import { useEffect, useState } from 'react'
import { MaterialsAPI } from '@/services/api'

export default function ReadingMaterials({ 
  selectedMaterial, 
  onMaterialSelect 
}) {
  const [materials, setMaterials] = useState([])
  const [factories, setFactories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedFactory, setSelectedFactory] = useState(null)

  // 获取工厂列表
  useEffect(() => {
    const fetchFactories = async () => {
      try {
        const response = await MaterialsAPI.getAll()
        setFactories(response)
        // 如果有工厂,默认选择第一个
        if (response.length > 0) {
          setSelectedFactory(response[0].id)
        }
      } catch (err) {
        console.error('Failed to fetch factories:', err)
        setError('Failed to load factories')
      }
    }

    fetchFactories()
  }, [])

  // 当选择的工厂改变时,获取该工厂的材料
  useEffect(() => {
    const fetchMaterials = async () => {
      if (!selectedFactory) return

      try {
        setLoading(true)
        const response = await MaterialsAPI.getMaterialsByFactory(selectedFactory)
        setMaterials(response.materials || [])
      } catch (err) {
        console.error('Failed to fetch materials:', err)
        setError('Failed to load materials')
      } finally {
        setLoading(false)
      }
    }

    fetchMaterials()
  }, [selectedFactory])

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
    <nav className="w-64 border-r border-neutral-200 bg-slate-50 p-4">
      {/* 工厂选择器 */}
      <select
        className="w-full mb-4 p-2 rounded border border-gray-300"
        value={selectedFactory || ''}
        onChange={(e) => setSelectedFactory(e.target.value)}
      >
        <option value="">Select Factory</option>
        {factories.map((factory) => (
          <option key={factory.id} value={factory.id}>
            {factory.name}
          </option>
        ))}
      </select>

      <h2 className="mb-4 text-lg font-semibold text-gray-900">Reading Materials</h2>
      
      {materials.length === 0 ? (
        <p className="text-gray-500 text-sm">
          {selectedFactory 
            ? 'No materials available in this factory' 
            : 'Please select a factory'}
        </p>
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
    </nav>
  )
}
