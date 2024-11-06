'use client'

import { useParams } from 'next/navigation'
import React, { useState, useEffect } from 'react'
import AIExplanation from './components/AIExplanation'
import ReadingMaterials from './components/ReadingMaterials'
import { MaterialsAPI } from '@/services/api'  // 修正导入路径
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import Link from 'next/link'


export default function TranslationLearningPage() {
  const params = useParams()
  const [selectedMaterial, setSelectedMaterial] = useState(null)
  const [showTranslation, setShowTranslation] = useState(false)
  const [selectedSentence, setSelectedSentence] = useState(null)
  const [segments, setSegments] = useState([])
  const [loading, setLoading] = useState(true)
  const [materials, setMaterials] = useState([])

  const fetchSegments = async (materialId) => {
    try {
      setLoading(true)
      const response = await MaterialsAPI.getSegments(materialId)
      setSegments(response.data || [])
    } catch (error) {
      console.error('Failed to fetch segments:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleMaterialSelect = (materialId) => {
    setSelectedMaterial(materialId)
    fetchSegments(materialId)
  }

  useEffect(() => {
    const fetchMaterials = async () => {
      try {
        const response = await MaterialsAPI.getMaterialsByFactory(params.id)
        setMaterials(response.materials || [])
      } catch (error) {
        console.error('Failed to fetch materials:', error)
      }
    }
    fetchMaterials()
  }, [params.id])

  return (
    <div className="flex h-screen bg-white text-gray-900">
      {/* Left Navigation */}
      <ReadingMaterials 
        selectedMaterial={selectedMaterial}
        onMaterialSelect={handleMaterialSelect}
      />

      {/* Middle Reading Area */}
      <main className="flex-1 overflow-auto p-6 bg-white">
        {loading ? (
          <div>加载或等待用户选择文字中😊...</div>
        ) : segments.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <ExclamationTriangleIcon className="h-12 w-12 text-yellow-500 mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              该材料尚未进行分段和翻译
            </h2>
            <p className="text-gray-600 mb-4">
              请先完成材料的分段和翻译设置
            </p>
            <Link 
              href={`/${params.locale}/material/create?materialId=${selectedMaterial}&step=2`}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              前往分段设置
            </Link>
          </div>
        ) : (
          <div>
            {/* 修改后的标题显示 */}
            <h1 className="text-2xl font-semibold text-gray-900 mb-4">
              {materials.find(m => m._id === selectedMaterial)?.title || '请选择阅读材料'}
            </h1>

            <button
              onClick={() => setShowTranslation(!showTranslation)}
              className="mb-6 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              {showTranslation ? '隐藏翻译' : '显示翻译'}
            </button>

            {/* 原有的段落渲染代码 */}
            {(() => {
              // 按段落分组
              const paragraphs = [];
              let currentParagraph = [];

              segments.forEach((segment) => {
                if (segment.is_new_paragraph) {
                  if (currentParagraph.length > 0) {
                    paragraphs.push(currentParagraph);
                  }
                  currentParagraph = [segment];
                } else {
                  currentParagraph.push(segment);
                }
              });

              if (currentParagraph.length > 0) {
                paragraphs.push(currentParagraph);
              }

              return paragraphs.map((paragraph, paraIndex) => (
                <div key={paraIndex} className={`${paraIndex > 0 ? 'mt-4' : ''}`}>
                  {paragraph.map((segment) => (
                    <span key={segment._id} className="inline">
                      <span
                        className={`border-b-2 ${
                          selectedSentence === segment.original 
                            ? 'border-blue-400' 
                            : 'border-transparent hover:border-gray-200'
                        }`}
                        onClick={() => setSelectedSentence(segment.original)}
                      >
                        {segment.original}
                      </span>
                      {showTranslation && (
                        <div className="mt-2 text-gray-600">
                          {segment.translation}
                        </div>
                      )}
                    </span>
                  ))}
                </div>
              ));
            })()}
          </div>
        )}
      </main>

      {/* Right AI Explanation */}
      <AIExplanation 
        selectedSentence={selectedSentence}
        content={segments}
        selectedMaterial={selectedMaterial}
      />
    </div>
  )
}