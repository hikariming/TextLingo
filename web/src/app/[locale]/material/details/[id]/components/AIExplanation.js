'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatBubbleLeftRightIcon, StarIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { VocabularyAPI } from '@/services/api'
import { GrammarAPI } from '@/services/api'
import { toast } from 'react-hot-toast' // 需要安装 react-hot-toast

export default function AIExplanation({ selectedSentence, content }) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [width, setWidth] = useState(320) // 默认宽度320px
  const [isDragging, setIsDragging] = useState(false)
  const dragStartX = useRef(0)
  const dragStartWidth = useRef(0)
  const longPressTimer = useRef(null)
  const isLongPress = useRef(false)
  const [savedWordsMap, setSavedWordsMap] = useState({})
  const [savedGrammarsMap, setSavedGrammarsMap] = useState({})

  // 当解释内容更新时,检查所有单词的收藏状态
  useEffect(() => {
    const checkSavedStatus = async () => {
      // 确保选中了句子且有词汇数据
      const selectedSegment = content?.find(
        segment => segment.original === selectedSentence
      )
      
      if (!selectedSegment?.vocabulary?.length) return
      
      try {
        // 获取当前选中段落中的所有单词
        const wordsToCheck = selectedSegment.vocabulary.map(vocab => vocab.word)
        
        // 批量检查收藏状态
        const response = await VocabularyAPI.checkSavedWords(wordsToCheck)
        if (response.success) {
          setSavedWordsMap(response.data)
        }
      } catch (error) {
        console.error('检查收藏状态失败:', error)
      }
    }

    checkSavedStatus()
  }, [selectedSentence, content]) // 当选中的句子或内容变化时重新检查

  // 添加检查语法点状态的效果
  useEffect(() => {
    const checkGrammarStatus = async () => {
      const selectedSegment = content?.find(
        segment => segment.original === selectedSentence
      )
      
      if (!selectedSegment?.grammar?.length) return
      
      try {
        const grammarsToCheck = selectedSegment.grammar.map(gram => gram.name)
        const response = await GrammarAPI.checkSavedGrammars(grammarsToCheck)
        if (response.success) {
          setSavedGrammarsMap(response.data)
        }
      } catch (error) {
        console.error('检查语法点状态失败:', error)
      }
    }

    checkGrammarStatus()
  }, [selectedSentence, content])

  // 处理拖动开始
  const handleDragStart = (e) => {
    setIsDragging(true)
    dragStartX.current = e.clientX
    dragStartWidth.current = width
    document.body.style.cursor = 'col-resize'
  }

  // 处理箭头按钮的鼠标事件
  const handleButtonMouseDown = (e) => {
    longPressTimer.current = setTimeout(() => {
      isLongPress.current = true
      handleDragStart(e)
    }, 200) // 200ms后触发长按
  }

  const handleButtonMouseUp = () => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
    }
    if (!isLongPress.current) {
      setIsCollapsed(!isCollapsed)
    }
    isLongPress.current = false
  }

  const handleButtonMouseLeave = () => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
    }
  }

  // 处理拖动过程
  useEffect(() => {
    const handleDrag = (e) => {
      if (!isDragging) return
      const delta = dragStartX.current - e.clientX
      const newWidth = Math.max(280, Math.min(800, dragStartWidth.current + delta))
      setWidth(newWidth)
    }

    const handleDragEnd = () => {
      setIsDragging(false)
      document.body.style.cursor = ''
    }

    if (isDragging) {
      window.addEventListener('mousemove', handleDrag)
      window.addEventListener('mouseup', handleDragEnd)
    }

    return () => {
      window.removeEventListener('mousemove', handleDrag)
      window.removeEventListener('mouseup', handleDragEnd)
    }
  }, [isDragging])

  // 直接从content数组中查找匹配的segment
  const selectedSegment = content?.find(
    segment => segment.original === selectedSentence
  )

  // 处理收藏/取消收藏单词
  const handleSaveVocabulary = async (vocab) => {
    try {
      if (savedWordsMap[vocab.word]) {
        // 取消收藏
        await VocabularyAPI.delete(savedWordsMap[vocab.word])
        setSavedWordsMap(prev => {
          const newMap = { ...prev }
          delete newMap[vocab.word]
          return newMap
        })
        toast.success('已取消收藏')
      } else {
        // 添加收藏
        const response = await VocabularyAPI.create({
          word: vocab.word,
          reading: vocab.reading || '',
          meaning: vocab.meaning,
          source_segment_id: selectedSegment?._id
        })
        
        if (response.success) {
          setSavedWordsMap(prev => ({
            ...prev,
            [vocab.word]: response.data._id
          }))
          toast.success('单词已添加到生词本')
        }
      }
    } catch (error) {
      console.error('操作失败:', error)
      toast.error('操作失败，请重试')
    }
  }

  // 添加处理保存语法点的函数
  const handleSaveGrammar = async (grammar) => {
    try {
      if (savedGrammarsMap[grammar.name]) {
        // 取消保存
        await GrammarAPI.delete(savedGrammarsMap[grammar.name])
        setSavedGrammarsMap(prev => {
          const newMap = { ...prev }
          delete newMap[grammar.name]
          return newMap
        })
        toast.success('已取消保存语法点')
      } else {
        // 添加保存
        const response = await GrammarAPI.create({
          name: grammar.name,
          explanation: grammar.explanation,
          source_segment_id: selectedSegment?._id
        })
        
        if (response.success) {
          setSavedGrammarsMap(prev => ({
            ...prev,
            [grammar.name]: response.data._id
          }))
          toast.success('语法点已保存')
        }
      }
    } catch (error) {
      console.error('操作失败:', error)
      toast.error('操作失败，请重试')
    }
  }

  return (
    <aside className={`relative flex transition-all duration-300 ease-in-out ${isCollapsed ? 'w-12' : ''}`}>
      {/* 拖动条 */}
      <div
        className="absolute left-0 top-0 w-1 h-full cursor-col-resize hover:bg-blue-200 active:bg-blue-300"
        onMouseDown={handleDragStart}
      />

      {/* 折叠按钮 */}
      <button
        onMouseDown={handleButtonMouseDown}
        onMouseUp={handleButtonMouseUp}
        onMouseLeave={handleButtonMouseLeave}
        className="absolute -left-3 top-1/2 z-10 transform -translate-y-1/2 bg-white rounded-full p-1 shadow-md hover:bg-gray-100"
      >
        <ChevronRightIcon 
          className={`h-4 w-4 text-gray-600 transition-transform duration-300 ${isCollapsed ? '' : 'rotate-180'}`}
        />
      </button>

      {/* 主内容区域 */}
      <div 
        style={{ width: isCollapsed ? 0 : width }}
        className={`overflow-hidden border-l border-neutral-200 bg-slate-50 transition-all duration-300 ${isCollapsed ? 'opacity-0' : 'opacity-100'}`}
      >
        <div className="p-4 h-[calc(100vh-4rem)] overflow-y-auto">
          <h2 className="mb-4 flex items-center text-lg font-semibold text-gray-900">
            <ChatBubbleLeftRightIcon className="mr-2 h-5 w-5 text-blue-600" />
            AI Explanation
          </h2>
          
          {!selectedSentence ? (
            <div className="flex flex-col items-center justify-center text-center text-gray-500 mt-8">
              <ChatBubbleLeftRightIcon className="h-12 w-12 mb-4" />
              <p className="text-lg font-medium">点击左侧文本开始学习</p>
              <p className="text-sm mt-2">选择任意句子，获取详细的语法解析和词汇讲解</p>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <p className="mb-2 font-medium text-gray-900">{selectedSentence}</p>
                <p className="text-sm text-gray-600">{selectedSegment?.translation}</p>
              </div>

              {/* 生词解释 */}
              <div>
                <h3 className="mb-2 font-medium text-gray-900">生词</h3>
                <div className="space-y-2">
                  {selectedSegment?.vocabulary?.map((vocab, index) => (
                    <div key={index} className="rounded-md bg-white p-3">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium text-gray-900">
                            {vocab.word}
                            {vocab.reading && `（${vocab.reading}）`}
                          </p>
                          <p className="text-sm text-gray-600">{vocab.meaning}</p>
                        </div>
                        <button 
                          className="group relative p-1 hover:bg-gray-100 rounded-full"
                          onClick={() => handleSaveVocabulary(vocab)}
                          aria-label="添加到生词本"
                        >
                          <StarIcon 
                            className={`h-5 w-5 ${
                              savedWordsMap[vocab.word]
                                ? 'text-yellow-400' 
                                : 'text-gray-400 hover:text-yellow-400'
                            }`} 
                          />
                          <span className="absolute -top-8 left-1/2 -translate-x-1/2 hidden group-hover:block bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                            {savedWordsMap[vocab.word] ? '取消收藏' : '添加到生词本'}
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
                    {selectedSegment?.grammar?.map((point, index) => (
                      <li key={index} className="flex justify-between items-start gap-2">
                        <div>
                          <p className="font-medium text-gray-900">{point.name}</p>
                          <p className="text-sm text-gray-600">{point.explanation}</p>
                        </div>
                        <button 
                          className="group relative p-1 hover:bg-gray-100 rounded-full flex-shrink-0"
                          onClick={() => handleSaveGrammar(point)}
                          aria-label="添加到语法笔记"
                        >
                          <StarIcon 
                            className={`h-5 w-5 ${
                              savedGrammarsMap[point.name]
                                ? 'text-yellow-400' 
                                : 'text-gray-400 hover:text-yellow-400'
                            }`}
                          />
                          <span className="absolute -top-8 right-0 hidden group-hover:block bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                            {savedGrammarsMap[point.name] ? '取消保存' : '添加到语法笔记'}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}
