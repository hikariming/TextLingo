'use client'

import { useState } from 'react'
import { MagnifyingGlassIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'

export default function KnowledgeContent({ initialGrammars = [] }) {
  const [expandedItems, setExpandedItems] = useState([])
  const [searchTerm, setSearchTerm] = useState('')

  const toggleExpand = (id) => {
    setExpandedItems(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    )
  }

  const filteredKnowledge = initialGrammars.filter(item => 
    item.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.explanation?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <>
      <h1 className="text-2xl font-bold mb-6 text-center text-black">已保存的知识(该功能还在开发中！deving....)</h1>
      
      {/* 搜索框 */}
      <div className="relative mb-6">
        <input
          type="text"
          placeholder="搜索知识..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-10 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
      </div>

      {/* 知识卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredKnowledge.map((item) => (
          <div key={item.id} className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-black">{item.title}</h3>
              <button
                onClick={() => toggleExpand(item.id)}
                className="text-blue-600 hover:text-blue-700"
              >
                {expandedItems.includes(item.id) ? 
                  <ChevronUpIcon className="w-5 h-5" /> : 
                  <ChevronDownIcon className="w-5 h-5" />
                }
              </button>
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-2">{item.explanation}</p>
              {expandedItems.includes(item.id) && (
                <div className="mt-4">
                  {item.sourceSegmentId && (
                    <p className="text-xs text-gray-500">来源ID: {item.sourceSegmentId}</p>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}