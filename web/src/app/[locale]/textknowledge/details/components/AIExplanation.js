'use client'

import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline'

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
                <p className="font-medium text-gray-900">{vocab.word}（{vocab.reading}）</p>
                <p className="text-sm text-gray-600">{vocab.meaning}</p>
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
                <li key={index}>• {point}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </aside>
  )
}
