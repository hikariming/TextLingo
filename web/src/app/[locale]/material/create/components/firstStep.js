import { ArrowLeftIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline'
import { useState, useRef } from 'react'

export default function DataSourceSelector({ t, onNext }) {
  const [selectedSource, setSelectedSource] = useState('text')
  const [inputText, setInputText] = useState('')
  const [webUrl, setWebUrl] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

  const dataSourceOptions = [
    {
      id: 'text',
      icon: '📄',
      title: '导入已有文本',
      primary: true
    },
    {
      id: 'input',
      icon: 'N',
      title: '直接输入文本'
    },
    {
      id: 'web',
      icon: '🌐',
      title: '同步自 Web 站点(会消耗Token)'
    }
  ]

  const handleOptionClick = (optionId) => {
    setSelectedSource(optionId)
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    const files = e.dataTransfer.files
    if (files?.[0]) {
      await handleFile(files[0])
    }
  }

  const handleFileInput = async (e) => {
    const files = e.target.files
    if (files?.[0]) {
      await handleFile(files[0])
    }
  }

  const handleFile = async (file) => {
    // Check file size (15MB)
    if (file.size > 15 * 1024 * 1024) {
      alert('文件大小不能超过15MB')
      return
    }

    // Check file type
    const extension = file.name.split('.').pop().toLowerCase()
    const allowedTypes = ['txt', 'markdown', 'pdf', 'html', 'xlsx', 'xls', 'docx', 'csv', 'md', 'htm']
    if (!allowedTypes.includes(extension)) {
      alert('不支持的文件类型')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://127.0.0.1:5000/api/materials', {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        throw new Error('Upload failed')
      }

      // 上传成功后调用onNext
      onNext()
    } catch (error) {
      alert('文件上传失败: ' + error.message)
    }
  }

  const textSourceJSX = (
    <div 
      className={`border-2 border-dashed rounded-lg p-6 bg-neutral-100
        ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileInput}
        accept=".txt,.markdown,.pdf,.html,.xlsx,.xls,.docx,.csv,.md,.htm"
      />
      <div className="text-center">
        <ArrowUpTrayIcon className="mx-auto h-10 w-10 text-gray-400" />
        <div className="mt-3">
          <p className="text-gray-600 text-sm">
            拖拽文件至此，或者{' '}
            <button 
              className="text-blue-600 hover:text-blue-700"
              onClick={() => fileInputRef.current?.click()}
            >
              选择文件
            </button>
          </p>
          <p className="mt-2 text-xs text-gray-500">
            已支持 TXT、MARKDOWN、PDF、HTML、XLSX、XLS、DOCX、CSV、MD、HTM，每个文件不超过15MB。
          </p>
        </div>
      </div>
    </div>
  )

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* 返回按钮 */}
      {/* <div className="mb-8">
        <button className="flex items-center text-blue-600 hover:text-blue-700">
          <ArrowLeftIcon className="h-4 w-4 mr-2" />
          <span>创建素材库</span>
        </button>
      </div> */}

      {/* 标题 */}
      <h1 className="text-xl font-semibold mb-6">选择数据源</h1>

      {/* 数据源选项 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {dataSourceOptions.map((option) => (
          <button
            key={option.id}
            onClick={() => handleOptionClick(option.id)}
            className={`p-3 rounded-lg border-2 flex items-center space-x-3 hover:border-blue-500 transition-colors ${
              selectedSource === option.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
            }`}
          >
            <span className="text-lg">{option.icon}</span>
            <span className="text-gray-900 text-sm">{option.title}</span>
          </button>
        ))}
      </div>

      {/* 根据选择显示不同的输入区域 */}
      {selectedSource === 'text' && textSourceJSX}

      {selectedSource === 'input' && (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 bg-neutral-100">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            className="w-full h-40 p-3 border border-gray-300 rounded-md"
            placeholder="请直接输入文本内容..."
          />
        </div>
      )}

      {selectedSource === 'web' && (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 bg-neutral-100">
          <input
            type="url"
            value={webUrl}
            onChange={(e) => setWebUrl(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-md"
            placeholder="请输入网页URL..."
          />
          <p className="mt-2 text-xs text-gray-500">
            请输入有效的网页URL，系统将自动抓取内容
          </p>
        </div>
      )}

      {/* 创建空素材库按钮 */}
      <div className="mt-6">
        <button className="text-blue-600 hover:text-blue-700 flex items-center text-sm">
          <span className="mr-2">+</span>
          创建一个空素材库
        </button>
      </div>

      {/* 添加底部操作按钮 */}
      <div className="mt-6 flex justify-end space-x-4">
        <button 
          onClick={onNext}
          disabled={!selectedSource}
          className={`px-4 py-2 text-white rounded-md ${
            selectedSource ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-400 cursor-not-allowed'
          }`}
        >
          下一步
        </button>
      </div>
    </div>
  )
}