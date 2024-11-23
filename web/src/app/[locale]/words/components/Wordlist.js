'use client'
import { useState, useEffect } from 'react'
import { EyeIcon, EyeSlashIcon, ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline"
import { VocabularyAPI } from '@/services/api'

function WordList({ initialWords }) {
  const [showTranslations, setShowTranslations] = useState(false)
  const [words] = useState(initialWords)
  const [expandedWords, setExpandedWords] = useState(words.map(() => false))
  const [wordSources, setWordSources] = useState(words.map(() => null))
  const [loadingStates, setLoadingStates] = useState(words.map(() => false))
  const [cardsPerRow, setCardsPerRow] = useState(3)

  useEffect(() => {
    const updateCardsPerRow = () => {
      if (window.innerWidth < 768) {
        setCardsPerRow(1)
      } else if (window.innerWidth < 1024) {
        setCardsPerRow(2)
      } else {
        setCardsPerRow(3)
      }
    }

    updateCardsPerRow()
    window.addEventListener('resize', updateCardsPerRow)
    return () => window.removeEventListener('resize', updateCardsPerRow)
  }, [])

  const toggleTranslations = () => {
    setShowTranslations(!showTranslations)
  }

  const toggleWordSources = async (index) => {
    const rowStart = Math.floor(index / cardsPerRow) * cardsPerRow
    const rowEnd = Math.min(rowStart + cardsPerRow, words.length)
    
    const newExpandedState = !expandedWords[index]
    
    setExpandedWords(prev => {
      const newExpandedWords = [...prev]
      for (let i = rowStart; i < rowEnd; i++) {
        newExpandedWords[i] = newExpandedState
      }
      return newExpandedWords
    })

    for (let i = rowStart; i < rowEnd; i++) {
      if (newExpandedState && !wordSources[i]) {
        setLoadingStates(prev => {
          const newLoadingStates = [...prev]
          newLoadingStates[i] = true
          return newLoadingStates
        })

        try {
          const response = await VocabularyAPI.getSources(words[i].id)
          setWordSources(prev => {
            const newWordSources = [...prev]
            newWordSources[i] = response.data.sources
            return newWordSources
          })
        } catch (error) {
          console.error('获取单词来源失败:', error)
        } finally {
          setLoadingStates(prev => {
            const newLoadingStates = [...prev]
            newLoadingStates[i] = false
            return newLoadingStates
          })
        }
      }
    }
  }

  return (
    <div className="space-y-4">
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

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {words.map((word, index) => (
          <div
            key={word.id}
            className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 flex flex-col"
          >
            <div className="flex justify-between items-center w-full">
              <h3 className="text-lg font-medium text-gray-900">{word.word}</h3>
              <button
                onClick={() => toggleWordSources(index)}
                className="text-gray-500 hover:text-gray-700"
              >
                {expandedWords[index] ? (
                  <ChevronUpIcon className="h-5 w-5" />
                ) : (
                  <ChevronDownIcon className="h-5 w-5" />
                )}
              </button>
            </div>
            
            {showTranslations && (
              <div className="mt-2 w-full">
                <p className="text-gray-600">{word.translation}</p>
                {word.example && (
                  <p className="mt-2 text-sm text-gray-500 italic">
                    例句: {word.example}
                  </p>
                )}
              </div>
            )}

            <div className={`mt-4 border-t pt-4 w-full ${expandedWords[index] ? '' : 'hidden'}`}>
              <h4 className="text-sm font-medium text-gray-700 mb-2">出现位置：</h4>
              {loadingStates[index] ? (
                <p className="text-sm text-gray-500">加载中...</p>
              ) : wordSources[index]?.length > 0 ? (
                <div className="space-y-3">
                  {wordSources[index].map((source, sourceIndex) => (
                    <div key={sourceIndex} className="text-sm">
                      <p className="text-gray-800">{source.original}</p>
                      <p className="text-gray-600 mt-1">{source.translation}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">暂无来源记录</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {words.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          还没有收藏任何词汇
        </div>
      )}
    </div>
  )
}

export default WordList