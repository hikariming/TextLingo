'use client'

import { useState } from 'react'
import { MagnifyingGlassIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'

export default function KnowledgeContent({ initialKnowledge }) {
  const [expandedItems, setExpandedItems] = useState([])
  const [searchTerm, setSearchTerm] = useState('')

  const toggleExpand = (id) => {
    setExpandedItems(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    )
  }

  const filteredKnowledge = initialKnowledge.filter(item => 
    item.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.sentence?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.translation?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <>
      <h1 className="text-2xl font-bold mb-6 text-center text-black">已保存的知识</h1>
      
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
              <h3 className="text-lg font-medium text-black">
                {item.type === 'grammar' ? item.title : '句子分析'}
              </h3>
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

            {item.type === 'grammar' ? (
              <div>
                <p className="text-sm text-gray-600 mb-2">{item.explanation}</p>
                {expandedItems.includes(item.id) && (
                  <div className="mt-4">
                    <h4 className="font-semibold mb-2 text-black">例句：</h4>
                    {item.examples.map((example, index) => (
                      <div key={index} className="mb-3 p-2 bg-gray-50 rounded">
                        <p className="font-medium text-black">{example.sentence}</p>
                        <p className="text-sm text-gray-600">{example.translation}</p>
                        <p className="text-xs text-gray-500">{example.explanation}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div>
                <p className="font-medium text-black">{item.sentence}</p>
                <p className="text-sm text-gray-600 mb-2">{item.translation}</p>
                {expandedItems.includes(item.id) && (
                  <div className="mt-4">
                    <p className="text-sm text-gray-600">{item.explanation}</p>
                    <h4 className="font-semibold mt-2 mb-1 text-black">语法要点：</h4>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {item.grammarPoints?.map((point, index) => (
                        <li key={index}>{point}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  )
}