import { ArrowLeftIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline'
import { useState, useRef } from 'react'
import { MaterialsAPI } from '@/services/api'
import { useSearchParams } from 'next/navigation'

export default function DataSourceSelector({ onNext }) {
  const [selectedSource, setSelectedSource] = useState('text')
  const [inputText, setInputText] = useState('')
  const [webUrl, setWebUrl] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)
  const [isUploaded, setIsUploaded] = useState(false)
  const [materialId, setMaterialId] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [inputTitle, setInputTitle] = useState('')

  const searchParams = useSearchParams()
  const factoryId = searchParams.get('factoryId')


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

    setIsUploading(true)
    try {
      const res = await MaterialsAPI.uploadFile(file, factoryId)
      console.log('res', res)
      setIsUploaded(true)
      setMaterialId(res.data._id)
    } catch (error) {
      alert('文件上传失败: ' + error.message)
      setIsUploaded(false)
    } finally {
      setIsUploading(false)
    }
  }

  const handleTextSubmit = async () => {
    if (!inputText.trim()) {
      alert('请输入文本内容')
      return
    }
    
    if (!inputTitle.trim()) {
      alert('请输入标题')
      return
    }

    setIsUploading(true)
    try {
      const uploaddata = {
        content: inputText,
        title: inputTitle,
        factory_id: factoryId
      }
      const res = await MaterialsAPI.uploadText(uploaddata)
      setIsUploaded(true)
      setMaterialId(res.data._id)
    } catch (error) {
      alert('文本上传失败: ' + error.message)
      setIsUploaded(false)
    } finally {
      setIsUploading(false)
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
        {isUploading ? (
          <div className="flex flex-col items-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
            <p className="mt-3 text-gray-600">正在上传文件...</p>
          </div>
        ) : (
          <>
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
                已支持 TXT、MARKDOWN、DOCX，每个文件不超过15MB。
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )

  const handleNext = () => {
    onNext({
      materialId: materialId
    })
  }

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
          <div className="mb-4">
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                标题
            </label>
            <input
                id="title"
                type="text"
                value={inputTitle}
                onChange={(e) => setInputTitle(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-md"
                placeholder="请输入标题..."
            />
        </div>
        <div>
            <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2">
                内容
            </label>
            <textarea
                id="content"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="w-full h-40 p-3 border border-gray-300 rounded-md"
                placeholder="请直接输入文本内容..."
            />
        </div>
        <div className="mt-4 flex justify-end">
            <button
                onClick={handleTextSubmit}
                disabled={isUploading || !inputText.trim() || !inputTitle.trim()}
                className={`px-4 py-2 rounded-md ${
                    isUploading || !inputText.trim() || !inputTitle.trim()
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
            >
                {isUploading ? '正在上传...' : '确认上传'}
            </button>
        </div>
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

  

      {/* 添加底部操作按钮 */}
      <div className="mt-6 flex justify-end space-x-4">
        <button 
          onClick={handleNext}
          disabled={!selectedSource || (selectedSource === 'text' && !isUploaded)}
          className={`px-4 py-2 text-white rounded-md ${
            selectedSource && (selectedSource !== 'text' || isUploaded) 
              ? 'bg-blue-600 hover:bg-blue-700' 
              : 'bg-gray-400 cursor-not-allowed'
          }`}
        >
          下一步
        </button>
      </div>
    </div>
  )
}