import { ArrowPathIcon, DocumentTextIcon, AcademicCapIcon, CodeBracketIcon } from '@heroicons/react/24/outline'

export default function TextSegmentation({ onNext, onPrev }) {
  const segmentationOptions = [
    {
      id: 'paragraph',
      icon: <DocumentTextIcon className="h-5 w-5" />,
      title: '按自然段落',
      description: '根据文本的段落结构进行分段'
    },
    {
      id: 'punctuation',
      icon: <CodeBracketIcon className="h-5 w-5" />,
      title: '按标点符号',
      description: '按句号(。)或英文句号(.)进行分段'
    },
    {
      id: 'ai',
      icon: <AcademicCapIcon className="h-5 w-5" />,
      title: '智能分段',
      description: '使用AI分析文本语义进行智能分段'
    },
    {
      id: 'linebreak',
      icon: <CodeBracketIcon className="h-5 w-5" />,
      title: '按换行符',
      description: '按文本中的换行符进行分段'
    }
  ]

  return (
    <div className="h-screen flex flex-col">
      <h1 className="text-xl font-semibold p-4 border-b">文本分段与翻译</h1>
      
      <div className="flex-1 flex">
        {/* 左侧设置区域 - 调整宽度为固定像素 */}
        <div className="w-[520px] border-r overflow-y-auto">
          <div className="p-6">
            <h2 className="text-lg font-medium mb-4">分段方式</h2>
            <div className="space-y-3">
              {segmentationOptions.map((option) => (
                <div
                  key={option.id}
                  className="p-3 rounded-lg border-2 hover:border-blue-500 cursor-pointer"
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
              <h2 className="text-lg font-medium mb-4">翻译设置</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">目标语言</label>
                  <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                    <option>简体中文</option>
                    <option>English</option>
                    <option>日本語</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">是否开启全篇深度讲解功能</label>
                  <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                    <option>开启</option>
                    <option>关闭</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 右侧预览区域 - 修改样式使其占满剩余空间 */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          <div className="flex justify-between items-center p-6 pb-4">
            <h2 className="text-lg font-medium">分段预览</h2>
            <button className="flex items-center text-blue-600 hover:text-blue-700">
              <ArrowPathIcon className="h-4 w-4 mr-1" />
              重新分段
            </button>
          </div>
          
          {/* 修改预览内容区域的样式 */}
          <div className="flex-1 overflow-y-auto px-6 pb-6">
            <div className="space-y-4 h-full ">
              {/* 分段预览列表 */}
              <div className="border rounded-lg p-4">
                <div className="flex justify-between text-sm text-gray-500 mb-2">
                  <span>段落 1</span>
                  <span>字数：120</span>
                </div>
                <p className="text-gray-800">这是第一段示例文本内容...</p>
                <p className="text-gray-500 mt-2">English translation here...</p>
              </div>

              <div className="border rounded-lg p-4">
                <div className="flex justify-between text-sm text-gray-500 mb-2">
                  <span>段落 2</span>
                  <span>字数：85</span>
                </div>
                <p className="text-gray-800">这是第二段示例文本内容...</p>
                <p className="text-gray-500 mt-2">English translation here...</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 底部操作按钮 - 固定在底部 */}
      <div className="border-t p-4 flex justify-end space-x-4">
        <button 
          onClick={onPrev}
          className="px-4 py-2 border rounded-md hover:bg-gray-50"
        >
          上一步
        </button>
        <button 
          onClick={onNext}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          下一步
        </button>
      </div>
    </div>
  )
}