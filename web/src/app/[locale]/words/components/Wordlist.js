'use client'
import { useState } from 'react'
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline"

function WordList({ initialWords }) {
  const [showTranslations, setShowTranslations] = useState(false)
  const [words] = useState(initialWords)

  const toggleTranslations = () => {
    setShowTranslations(!showTranslations)
  }

  return (
    <div className="space-y-4">
      {/* 显示/隐藏翻译的按钮 */}
      <button
        onClick={toggleTranslations}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white rounded-md border border-gray-300 hover:bg-gray-50"
      >
        {showTranslations ? (
          <>
            <EyeSlashIcon className="h-5 w-5" />
            <span>隐藏翻译</span>
          </>
        ) : (
          <>
            <EyeIcon className="h-5 w-5" />
            <span>显示翻译</span>
          </>
        )}
      </button>

      {/* 词汇列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {words.map((word) => (
          <div
            key={word.id}
            className="bg-white p-4 rounded-lg shadow-sm border border-gray-200"
          >
            <h3 className="text-lg font-medium text-gray-900">{word.word}</h3>
            {showTranslations && (
              <div className="mt-2">
                <p className="text-gray-600">{word.translation}</p>
                {word.example && (
                  <p className="mt-2 text-sm text-gray-500 italic">
                    例句: {word.example}
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 如果没有词汇，显示提示信息 */}
      {words.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          还没有收藏任何词汇
        </div>
      )}
    </div>
  )
}

export default WordList