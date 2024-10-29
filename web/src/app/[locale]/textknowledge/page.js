import { ArrowLeftIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline'

export default function DataSourceSelector({ t }) {
  const dataSourceOptions = [
    {
      id: 'text',
      icon: '📄',
      title: '导入已有文本',
      primary: true
    },
    {
      id: 'notion',
      icon: 'N',
      title: '同步自 Notion 内容'
    },
    {
      id: 'web',
      icon: '🌐',
      title: '同步自 Web 站点'
    }
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* 返回按钮 */}
      <div className="mb-8">
        <button className="flex items-center text-blue-600 hover:text-blue-700">
          <ArrowLeftIcon className="h-4 w-4 mr-2" />
          <span>创建知识库</span>
        </button>
      </div>

      {/* 标题 */}
      <h1 className="text-2xl font-bold mb-8">选择数据源</h1>

      {/* 数据源选项 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
        {dataSourceOptions.map((option) => (
          <button
            key={option.id}
            className={`p-4 rounded-lg border-2 flex items-center space-x-3 hover:border-blue-500 transition-colors ${
              option.primary ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
            }`}
          >
            <span className="text-xl">{option.icon}</span>
            <span className="text-gray-900">{option.title}</span>
          </button>
        ))}
      </div>

      {/* 文件上传区域 */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 bg-neutral-100">
        <div className="text-center">
          <ArrowUpTrayIcon className="mx-auto h-12 w-12 text-gray-400" />
          <div className="mt-4">
            <p className="text-gray-600">
              拖拽文件至此，或者{' '}
              <button className="text-blue-600 hover:text-blue-700">选择文件</button>
            </p>
            <p className="mt-2 text-sm text-gray-500">
              已支持 TXT、MARKDOWN、PDF、HTML、XLSX、XLS、DOCX、CSV、MD、HTM，每个文件不超过15MB。
            </p>
          </div>
        </div>
      </div>

      {/* 创建空知识库按钮 */}
      <div className="mt-8">
        <button className="text-blue-600 hover:text-blue-700 flex items-center">
          <span className="mr-2">+</span>
          创建一个空知识库
        </button>
      </div>
    </div>
  )
}