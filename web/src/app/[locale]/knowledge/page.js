import Navbar from '../../components/navigation/Navbar'
import KnowledgeContent from './components/KnowledgeContent'

export default async function KnowledgePage() {
  const savedKnowledge = [
    {
      id: 1,
      type: 'grammar',
      title: 'て-form',
      explanation: 'て-form是日语中常用的动词形式，用于连接动作、请求和复合动词。',
      examples: [
        { sentence: '食べて寝る', translation: '吃了睡觉', explanation: '连接两个动作' },
        { sentence: '窓を開けてください', translation: '请打开窗户', explanation: '礼貌请求' }
      ]
    },
    // ... 其他数据保持不变
  ]

  return (
    <>
      <Navbar />
      <div className="bg-slate-100 min-h-screen">
        <div className="container mx-auto p-4">
          <KnowledgeContent initialKnowledge={savedKnowledge} />
        </div>
      </div>
    </>
  )
}