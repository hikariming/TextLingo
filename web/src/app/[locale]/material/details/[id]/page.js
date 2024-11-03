'use client'

import { useParams } from 'next/navigation'
import React, { useState, useEffect } from 'react'
import AIExplanation from './components/AIExplanation'
import ReadingMaterials from './components/ReadingMaterials'
import { MaterialsAPI } from '@/services/api'  // 修正导入路径


export default function TranslationLearningPage() {
  const params = useParams()
  const [selectedMaterial, setSelectedMaterial] = useState(null)
  const [showTranslation, setShowTranslation] = useState(false)
  const [selectedSentence, setSelectedSentence] = useState(null)
  const [segments, setSegments] = useState([])
  const [loading, setLoading] = useState(true)

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

  const readingMaterials = [
    { id: 'material1', title: '満ちてゆく 藤井风' },
    { id: 'material2', title: 'China\'s giant economy faces an equally giant crisis of confidence—and a growing deficit of accurate information is only making things worse.' },
  ]

  return (
    <div className="flex h-screen bg-white text-gray-900">
      {/* Left Navigation */}
      <ReadingMaterials 
        readingMaterials={readingMaterials}
        selectedMaterial={selectedMaterial}
        onMaterialSelect={handleMaterialSelect}
      />

      {/* Middle Reading Area */}
      <main className="flex-1 overflow-auto p-6 bg-white">
        {loading ? (
          <div>Loading...</div>
        ) : (
          <div>
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