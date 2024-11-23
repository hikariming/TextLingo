'use client'
import { useState } from 'react'
import { EyeIcon, EyeSlashIcon, ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline"
import { VocabularyAPI } from '@/services/api'

function WordList({ initialWords }) {
  const [showTranslations, setShowTranslations] = useState(false)
  const [words] = useState(initialWords)
  const [expandedWords, setExpandedWords] = useState({})
  const [wordSources, setWordSources] = useState({})
  const [loadingStates, setLoadingStates] = useState({})

  const toggleTranslations = () => {
    setShowTranslations(!showTranslations)
  }

  const toggleWordSources = async (wordId) => {
    const isCurrentlyExpanded = expandedWords[wordId];
    
    setExpandedWords(prevState => ({
      ...prevState,
      [wordId]: !isCurrentlyExpanded
    }));

    if (!isCurrentlyExpanded && !wordSources[wordId]) {
      setLoadingStates(prevLoadingStates => ({
        ...prevLoadingStates,
        [wordId]: true
      }));

      try {
        const response = await VocabularyAPI.getSources(wordId);
        setWordSources(prevSources => ({
          ...prevSources,
          [wordId]: response.data.sources
        }));
      } catch (error) {
        console.error('获取单词来源失败:', error);
      } finally {
        setLoadingStates(prevLoadingStates => ({
          ...prevLoadingStates,
          [wordId]: false
        }));
      }
    }
  };

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
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900">{word.word}</h3>
              <button
                onClick={() => toggleWordSources(word.id)}
                className="text-gray-500 hover:text-gray-700"
              >
                {expandedWords[word.id] ? (
                  <ChevronUpIcon className="h-5 w-5" />
                ) : (
                  <ChevronDownIcon className="h-5 w-5" />
                )}
              </button>
            </div>
            
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

            {/* 单词来源展示区域 */}
            {expandedWords[word.id] && (
              <div className="mt-4 border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">出现位置：</h4>
                {loadingStates[word.id] ? (
                  <p className="text-sm text-gray-500">加载中...</p>
                ) : wordSources[word.id]?.length > 0 ? (
                  <div className="space-y-3">
                    {wordSources[word.id].map((source, index) => (
                      <div key={index} className="text-sm">
                        <p className="text-gray-800">{source.original}</p>
                        <p className="text-gray-600 mt-1">{source.translation}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">暂无来源记录</p>
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