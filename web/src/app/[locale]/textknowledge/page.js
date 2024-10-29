import FirstStep from './components/firstStep'
import Link from 'next/link'
import Navbar from '@/app/components/navigation/Navbar'
import { getTranslations } from 'next-intl/server'

export default async function TextKnowledge() {
  const t = await getTranslations()
  const steps = [
    { id: 1, title: '选择数据源', current: true },
    { id: 2, title: '文本分段与清洗', current: false },
    { id: 3, title: '处理并完成', current: false }
  ]

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar t={t} />
      <div className="flex flex-1">
        {/* 左侧导航栏 */}
        <div className="w-64 border-r bg-white">
          <div className="p-4">
            <Link href="/" className="text-blue-600 hover:text-blue-700 flex items-center">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              创建知识库
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
          <div className="max-w-2xl px-8 py-6">
            <FirstStep />
          </div>
        </div>
      </div>
    </div>
  )
}
