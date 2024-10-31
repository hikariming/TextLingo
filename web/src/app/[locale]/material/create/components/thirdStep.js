'use client'

export default function ThirdStep({ onPrev }) {
  return (
    <div className="p-6">
      {/* 标题部分 */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold">🎉 素材库已创建</h2>
        <p className="text-gray-600 mt-2">我们自动为该素材库起了个名称，您也可以随时修改</p>
      </div>

      {/* 素材库信息 */}
      <div className="bg-gray-50 p-6 rounded-lg mb-8">
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">素材库名称</label>
          <input 
            type="text" 
            className="w-full p-2 border rounded-md"
            defaultValue="14317738_20241024..."
            disabled
          />
        </div>

        {/* 处理状态信息 */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-gray-700">嵌入已完成</span>
            <span className="text-green-600">✓</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-700">分段规则</span>
            <span className="text-gray-600">自动</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-700">分段长度</span>
            <span className="text-gray-600">500</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-700">文本预定义与清洗</span>
            <span className="text-gray-600">自动</span>
          </div>
        </div>
      </div>

      {/* 下一步提示 */}
      <div className="bg-blue-50 p-6 rounded-lg mb-8">
        <h3 className="text-lg font-medium mb-2">🤔接下来做什么</h3>
        <p className="text-gray-600">
          文档目前已开始自动翻译，这需要一定的时间，您可目前可前往素材库详情页面查看翻译进度，也可直接前往阅读页面查看该文档的部分翻译。
        </p>
      </div>

      {/* 按钮区域 */}
      <div className="flex justify-between">
        <button
          onClick={onPrev}
          className="px-4 py-2 border rounded-md text-gray-600 hover:bg-gray-50"
        >
          上一步
        </button>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          onClick={() => window.location.href = '/'}
        >
          前往文档
        </button>
      </div>
    </div>
  )
}
