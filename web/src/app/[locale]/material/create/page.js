'use client'
import { useState } from 'react'
import FirstStep from './components/firstStep'
import SecondStep from './components/secondStep'
import ThirdStep from './components/thirdStep'
import Link from 'next/link'
// import Navbar from '@/app/components/navigation/Navbar'

export default function TextKnowledge() {
  const [currentStep, setCurrentStep] = useState(1)
  
  const steps = [
    { id: 1, title: '选择数据源', current: currentStep === 1 },
    { id: 2, title: '文本分段与翻译', current: currentStep === 2 },
    { id: 3, title: '处理并完成', current: currentStep === 3 }
  ]

  const handleNext = () => {
    setCurrentStep(prev => Math.min(prev + 1, 3))
  }

  const handlePrev = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1))
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* <Navbar t={t} /> */}
      <div className="flex flex-1">
        {/* 左侧导航栏 */}
        <div className="w-64 border-r bg-white">
          <div className="p-4">
            <Link href="/" className="text-blue-600 hover:text-blue-700 flex items-center">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              创建素材库
            </Link>
          </div>
          
          {/* 步骤列表 */}
          <nav className="mt-4">
            {steps.map((step) => (
              <div
                key={step.id}
                className={`px-4 py-2 flex items-center ${
                  step.current 
                    ? 'text-blue-600 bg-blue-50' 
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <span className={`mr-3 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center
                  ${step.current ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
                >
                  {step.id}
                </span>
                <span>{step.title}</span>
              </div>
            ))}
          </nav>
        </div>

        {/* 右侧内容区 */}
        <div className="flex-1">
          <div className="h-full">
            {currentStep === 1 && <FirstStep onNext={handleNext} />}
            {currentStep === 2 && <SecondStep onNext={handleNext} onPrev={handlePrev} />}
            {currentStep === 3 && <ThirdStep onPrev={handlePrev} />}
          </div>
        </div>
      </div>
    </div>
  )
}