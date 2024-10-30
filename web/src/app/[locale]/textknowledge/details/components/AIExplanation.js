'use client'

import { ChatBubbleLeftRightIcon, StarIcon } from '@heroicons/react/24/outline'

export default function AIExplanation({ selectedSentence, content, selectedMaterial }) {
  if (!selectedSentence) return null

  const selectedContent = content[selectedMaterial].find(
    item => item.original === selectedSentence
  )

  return (
    <aside className="w-80 border-l border-neutral-200 bg-slate-50 p-4">
      <h2 className="mb-4 flex items-center text-lg font-semibold text-gray-900">
        <ChatBubbleLeftRightIcon className="mr-2 h-5 w-5 text-blue-600" />
        AI Explanation
      </h2>
      <div className="space-y-6">
        <div>
          <p className="mb-2 font-medium text-gray-900">{selectedSentence}</p>
          <p className="text-sm text-gray-600">{selectedContent?.translation}</p>
        </div>

        {/* 生词解释 */}
        <div>
          <h3 className="mb-2 font-medium text-gray-900">生词</h3>
          <div className="space-y-2">
            {selectedContent?.vocabulary.map((vocab, index) => (
              <div key={index} className="rounded-md bg-white p-3">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">{vocab.word}（{vocab.reading}）</p>
                    <p className="text-sm text-gray-600">{vocab.meaning}</p>
                  </div>
                  <button 
                    className="group relative p-1 hover:bg-gray-100 rounded-full"
                    aria-label="添加到生词本"
                  >
                    <StarIcon className="h-5 w-5 text-gray-400 hover:text-yellow-400" />
                    <span className="absolute -top-8 left-1/2 -translate-x-1/2 hidden group-hover:block bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                      添加到生词本
                    </span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 语法解析 */}
        <div>
          <h3 className="mb-2 font-medium text-gray-900">语法解析</h3>
          <div className="rounded-md bg-white p-3">
            <ul className="text-sm text-gray-600 space-y-2">
              {selectedContent?.grammar.map((point, index) => (
                <li key={index} className="flex justify-between items-start gap-2">
                  <span>• {point}</span>
                  <button 
                    className="group relative p-1 hover:bg-gray-100 rounded-full flex-shrink-0"
                    aria-label="添加到语法笔记"
                  >
                    <StarIcon className="h-5 w-5 text-gray-400 hover:text-yellow-400" />
                    <span className="absolute -top-8 right-0 hidden group-hover:block bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                      添加到语法笔记
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </aside>
  )
}
