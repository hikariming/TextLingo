import { ArrowPathIcon, DocumentTextIcon, AcademicCapIcon, CodeBracketIcon } from '@heroicons/react/24/outline'
import { MaterialsAPI } from '@/services/api'
import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { SettingAPI } from '@/services/api'

export default function TextSegmentation({ onNext, onPrev, materialId }) {
  const [material, setMaterial] = useState(null)
  const [preview, setPreview] = useState([])
  const [selectedOption, setSelectedOption] = useState('paragraph')
  const [isLoading, setIsLoading] = useState(false)
  const [segments, setSegments] = useState([])
  const [error, setError] = useState(null)
  const [isSegmented, setIsSegmented] = useState(false)
  const [targetLanguage, setTargetLanguage] = useState('zh-CN')
  const [enableDeepExplanation, setEnableDeepExplanation] = useState(true)
  const [isTranslating, setIsTranslating] = useState(false)
  const [isTestingLLM, setIsTestingLLM] = useState(false)
  const [testMessage, setTestMessage] = useState('')

  const t = useTranslations('app.material.create.textSegmentation')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const materialResponse = await MaterialsAPI.getById(materialId)
        setMaterial(materialResponse.data)
        
        const previewResponse = await MaterialsAPI.getPreview(materialId)
        setPreview(previewResponse.data.preview)
      } catch (error) {
        console.error('Error fetching data:', error)
      }
    }

    if (materialId) {
      fetchData()
    }
  }, [materialId])

  console.log('Material ID in SecondStep:', materialId)

  const segmentationOptions = [
    {
      id: 'paragraph',
      icon: <DocumentTextIcon className="h-5 w-5" />,
      title: t('options.paragraph.title'),
      description: t('options.paragraph.description')
    },
    {
      id: 'ai',
      icon: <AcademicCapIcon className="h-5 w-5" />,
      title: t('options.ai.title'),
      description: t('options.ai.description'),
      disabled: true
    }
  ]

  const handleSegmentation = async () => {
    setIsLoading(true)
    setError(null)
    setIsSegmented(false)
    try {
      await MaterialsAPI.segmentMaterial(materialId, selectedOption)
      const segmentsResponse = await MaterialsAPI.getSegments(materialId)
      setSegments(segmentsResponse.data)
      setIsSegmented(true)
    } catch (error) {
      setError(error.message)
      console.error('Error during segmentation:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStartTranslation = async () => {
    setIsTranslating(true)
    setError(null)
    try {
      await MaterialsAPI.startTranslation(materialId, {
        target_language: targetLanguage,
        enable_deep_explanation: enableDeepExplanation
      })
      onNext({
        targetLanguage,
        enableDeepExplanation
      })
    } catch (error) {
      setError(error.message)
      console.error('Error starting translation:', error)
    } finally {
      setIsTranslating(false)
    }
  }

  const handleTestLLM = async () => {
    setIsTestingLLM(true)
    setTestMessage('')
    try {
      const result = await SettingAPI.testLLMConnection()
      setTestMessage(result.message)
    } catch (error) {
      setTestMessage(error.message)
    } finally {
      setIsTestingLLM(false)
    }
  }

  return (
    <div className="h-screen flex flex-col">
      <h1 className="text-xl font-semibold p-4 border-b">{t('title')}</h1>
      
      <div className="flex-1 flex">
        <div className="w-[520px] border-r flex flex-col">
          <div className="flex-1 overflow-y-auto">
            <div className="p-6">
              <h2 className="text-lg font-medium mb-4">{t('segmentationOptions')}</h2>
              <div className="space-y-3">
                {segmentationOptions.map((option) => (
                  <div
                    key={option.id}
                    className={`p-3 rounded-lg border-2 ${
                      option.disabled 
                        ? 'cursor-not-allowed opacity-50' 
                        : 'cursor-pointer ' + (selectedOption === option.id 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'hover:border-blue-500')
                    }`}
                    onClick={() => !option.disabled && setSelectedOption(option.id)}
                  >
                    <div className="flex items-center space-x-3">
                      <div className="text-gray-600">{option.icon}</div>
                      <div>
                        <div className="font-medium">{option.title}</div>
                        <div className="text-sm text-gray-500">{option.description}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6">
                <h2 className="text-lg font-medium mb-4">{t('translationSettings')}</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">{t('targetLanguage')}</label>
                    <select 
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                      value={targetLanguage}
                      onChange={(e) => setTargetLanguage(e.target.value)}
                    >
                      <option value="中文">{t('languageOptions.zh-CN')}</option>
                      <option value="英语">{t('languageOptions.en')}</option>
                      <option value="日语">{t('languageOptions.ja')}</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t('enableDeepExplanation')}
                    </label>
                    <select 
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                      value={enableDeepExplanation}
                      onChange={(e) => setEnableDeepExplanation(e.target.value === 'true')}
                    >
                      <option value="true">{t('toggleOptions.on')}</option>
                      <option value="false">{t('toggleOptions.off')}</option>
                    </select>
                  </div>
                  <div>
                    <button
                      type="button"
                      onClick={handleTestLLM}
                      disabled={isTestingLLM}
                      className="w-full px-4 py-2 text-white bg-green-600 rounded-md hover:bg-green-700 disabled:bg-gray-400"
                    >
                      {isTestingLLM ? t('testingLLM') : t('testLLM')}
                    </button>
                    {testMessage && (
                      <div className={`mt-2 p-2 rounded-md text-sm ${
                        testMessage.includes('成功') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {testMessage}
                      </div>
                    )}
                  </div>
                  <div className="border-t p-4 flex justify-end items-center space-x-4">
                    <button 
                      onClick={onPrev}
                      className="px-4 py-2 border rounded-md hover:bg-gray-50"
                      disabled={isTranslating}
                    >
                      {t('previousStep')}
                    </button>
                    <div className="relative">
                      <button 
                        onClick={handleStartTranslation}
                        disabled={!isSegmented}
                        className={`px-4 py-2 text-white rounded-md ${
                          isSegmented 
                            ? 'bg-blue-600 hover:bg-blue-700' 
                            : 'bg-gray-400 cursor-not-allowed'
                        }`}
                      >
                        {t('startTranslation')}
                      </button>
                      {!isSegmented && (
                        <div className="absolute top-full left-0 text-red-500 text-sm mt-1">
                          {t('pleaseSegmentText')}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          
        </div>

        <div className="flex-1 flex flex-col h-full overflow-hidden">
          <div className="flex justify-between items-center p-6 pb-4">
            <h2 className="text-lg font-medium">{t('segmentResult')}</h2>
            <button 
              className="flex items-center text-blue-600 hover:text-blue-700"
              onClick={handleSegmentation}
              disabled={isLoading}
            >
              <ArrowPathIcon className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
              {isLoading ? t('segmenting') : t('startSegmentation')}
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto px-6 pb-6">
            <div className="space-y-4">
              {segments.length > 0 ? (
                segments.map((segment, index) => (
                  <div key={segment.id} className="border rounded-lg p-4">
                    <div className="flex justify-between text-sm text-gray-500 mb-2">
                      <span>{t('paragraph', { index: index + 1 })}</span>
                      <span>{t('wordCount', { count: segment.original.length })}</span>
                    </div>
                    <p className="text-gray-800">{segment.original}</p>
                    <p className="text-gray-500 mt-2 italic">
                      {segment.translation || t('waitingTranslation')}
                    </p>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 mt-8">
                  {isLoading ? t('processingSegmentation') : t('clickToStartSegmentation')}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}