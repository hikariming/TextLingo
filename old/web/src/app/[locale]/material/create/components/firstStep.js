import { ArrowUpTrayIcon } from '@heroicons/react/24/outline'
import { useState, useRef } from 'react'
import { MaterialsAPI } from '@/services/api'
import { useSearchParams } from 'next/navigation'
import Notification from '../../../../components/Notification'
import { useTranslations } from 'next-intl'

export default function DataSourceSelector({ onNext }) {
  const t = useTranslations('app.material.create')
  const [selectedSource, setSelectedSource] = useState('text')
  const [inputText, setInputText] = useState('')
  const [webUrl, setWebUrl] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)
  const [isUploaded, setIsUploaded] = useState(false)
  const [materialId, setMaterialId] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [inputTitle, setInputTitle] = useState('')
  const [notification, setNotification] = useState(null)

  const searchParams = useSearchParams()
  const factoryId = searchParams.get('factoryId')


  const dataSourceOptions = [
    {
      id: 'text',
      icon: '📄',
      title: t('sources.existingText.title'),
      primary: true
    },
    {
      id: 'input',
      icon: 'N',
      title: t('sources.directInput.title')
    },
    {
      id: 'web',
      icon: '🌐',
      title: t('sources.web.title')
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
    if (file.size > 15 * 1024 * 1024) {
      alert(t('sources.existingText.sizeError'))
      return
    }

    const extension = file.name.split('.').pop().toLowerCase()
    const allowedTypes = ['txt', 'markdown', 'pdf', 'html', 'xlsx', 'xls', 'docx', 'csv', 'md', 'htm']
    if (!allowedTypes.includes(extension)) {
      alert(t('sources.existingText.typeError'))
      return
    }

    setIsUploading(true)
    try {
      const res = await MaterialsAPI.uploadFile(file, factoryId)
      setIsUploaded(true)
      setMaterialId(res.data._id)
      setNotification({
        message: t('sources.existingText.uploadSuccess'),
        type: 'success'
      })
    } catch (error) {
      setNotification({
        message: t('sources.existingText.uploadError') + error.message,
        type: 'error'
      })
      setIsUploaded(false)
    } finally {
      setIsUploading(false)
    }
  }

  const handleTextSubmit = async () => {
    if (!inputText.trim()) {
      setNotification({
        message: t('sources.directInput.emptyContent'),
        type: 'error'
      })
      return
    }
    
    if (!inputTitle.trim()) {
      setNotification({
        message: t('sources.directInput.emptyTitle'),
        type: 'error'
      })
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
      setNotification({
        message: t('sources.directInput.uploadSuccess'),
        type: 'success'
      })
    } catch (error) {
      setNotification({
        message: t('sources.directInput.uploadError') + error.message,
        type: 'error'
      })
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
                {t('sources.existingText.dragText')}
                <button 
                  className="text-blue-600 hover:text-blue-700"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {t('sources.existingText.selectFile')}
                </button>
              </p>
              <p className="mt-2 text-xs text-gray-500">
                {t('sources.existingText.supportedFormats')}
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
    <>
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="text-xl font-semibold mb-6">{t('selectDataSource')}</h1>

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

        {selectedSource === 'text' && textSourceJSX}

        {selectedSource === 'input' && (
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 bg-neutral-100">
            <div className="mb-4">
              <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                  {t('sources.directInput.titleLabel')}
              </label>
              <input
                  id="title"
                  type="text"
                  value={inputTitle}
                  onChange={(e) => setInputTitle(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-md"
                  placeholder={t('sources.directInput.titlePlaceholder')}
              />
          </div>
          <div>
              <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2">
                  {t('sources.directInput.contentLabel')}
              </label>
              <textarea
                  id="content"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  className="w-full h-40 p-3 border border-gray-300 rounded-md"
                  placeholder={t('sources.directInput.contentPlaceholder')}
              />
          </div>
          <div className="mt-4 flex justify-end">
              <button
                  onClick={handleTextSubmit}
                  disabled={isUploading || !inputText.trim() || !inputTitle.trim() || isUploaded}
                  className={`px-4 py-2 rounded-md ${
                      isUploading || !inputText.trim() || !inputTitle.trim() || isUploaded
                          ? 'bg-gray-400 cursor-not-allowed'
                          : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}
              >
                  {isUploading ? '正在上传...' : isUploaded ? '上传成功' : t('sources.directInput.confirm')}
              </button>
          </div>
        </div>
        )}

        {selectedSource === 'web' && (
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 bg-neutral-100">
            <div className="text-center text-gray-500">
              <p className="text-lg font-medium">{t('sources.web.comingSoon')}</p>
              <p className="text-sm mt-2">{t('sources.web.description')}</p>
            </div>
          </div>
        )}

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
            {t('next')}
          </button>
        </div>
      </div>
      {notification && (
        <Notification
          {...notification}
          onClose={() => setNotification(null)}
        />
      )}
    </>
  )
}