import Link from 'next/link'

export default function KnowledgeCards({ t }) {
  // 现有知识库数据示例
  const existingKnowledgeBases = [
    {
      title: 'Copy of 易智平台及易智助手',
      count: '1 文档',
      size: '13 千字符',
      usage: '0 知识'
    },
    // ... 其他知识库数据
  ]

  return (
    <div className="bg-neutral-100 min-h-screen">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4">
        {/* 新建知识库卡片 */}
        <div className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center mb-4">
            <div className="text-blue-600 text-xl">+</div>
            <h3 className="text-lg font-medium ml-2 text-black">创建文档库</h3>
          </div>
          <p className="text-black text-sm mb-4">
            新建知识库以导入链接，或PDF、Word、TXT、MD 等文档
          </p>
        
        </div>

        {/* 现有知识库卡片 */}
        {existingKnowledgeBases.map((kb, index) => (
          <div key={index} className="bg-white rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center mb-4">
              <div className="text-blue-600">📁</div>
              <h3 className="text-lg font-medium ml-2 text-black">{kb.title}</h3>
            </div>
            <div className="text-gray-500 text-xs">
              {kb.count} · {kb.size} · {kb.usage}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
} 