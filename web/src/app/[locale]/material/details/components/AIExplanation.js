'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatBubbleLeftRightIcon, StarIcon, ChevronRightIcon } from '@heroicons/react/24/outline'

export default function AIExplanation({ selectedSentence, content, selectedMaterial }) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [width, setWidth] = useState(320) // 默认宽度320px
  const [isDragging, setIsDragging] = useState(false)
  const dragStartX = useRef(0)
  const dragStartWidth = useRef(0)
  const longPressTimer = useRef(null)
  const isLongPress = useRef(false)

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

  const selectedContent = content[selectedMaterial].find(
    item => item.original === selectedSentence
  )

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
        <div className="p-4">
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
          )}
        </div>
      </div>
    </aside>
  )
}
