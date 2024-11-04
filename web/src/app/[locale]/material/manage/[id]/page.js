'use client'
import { useState } from 'react'
import Link from 'next/link'
import Navbar from '../../../../components/navigation/Navbar'

export default function MaterialManagement() {
  const [factory, setFactory] = useState({
    id: '1',
    name: '日语学习材料集',
    description: '包含多个日语学习材料的集合',
    materials: ['1', '2', '3'],
    created_at: '2024-03-15T10:00:00Z',
    updated_at: '2024-03-15T10:00:00Z'
  })

  const [materials, setMaterials] = useState([
    {
      _id: '1',
      title: '反转、暴击！这些视频在海外网站火了...',
      file_size: 4400,
      file_type: 'pdf',
      status: 'error',
      created_at: '2024-08-02T09:25:00Z',
      segments: ['seg1', 'seg2']
    }
  ])

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <div className="flex flex-1 pt-16">
        {/* 左侧边栏：显示材料集信息 */}
        <div className="w-80 border-r bg-white overflow-y-auto">
          {/* <div className="p-4">
            <Link href="/materials/factory" className="text-blue-600 hover:text-blue-700 flex items-center text-sm">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              返回材料集列表
            </Link>
          </div> */}

          <br />
          
          {/* 材料集详情 */}
          <div className="px-4">
            <div className="mb-6">
              <h2 className="text-xl font-medium mb-2">{factory.name}</h2>
              <p className="text-sm text-gray-600 mb-4">{factory.description}</p>
              
              <div className="text-xs text-gray-500 space-y-1">
                <div>创建时间：{new Date(factory.created_at).toLocaleString()}</div>
                <div>更新时间：{new Date(factory.updated_at).toLocaleString()}</div>
                <div>包含材料：{factory.materials.length} 个</div>
              </div>
            </div>

            <div className="mb-4">
              <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
                添加新材料
              </button>
            </div>

            <div className="border-t pt-4">
              <h3 className="text-sm font-medium mb-2">快速统计</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-xs text-gray-500">处理中</div>
                  <div className="text-lg font-medium">3</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-xs text-gray-500">已完成</div>
                  <div className="text-lg font-medium">12</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-xs text-gray-500">出错</div>
                  <div className="text-lg font-medium text-red-500">1</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-xs text-gray-500">总字数</div>
                  <div className="text-lg font-medium">5.2k</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 主要内容区域：材料列表 */}
        <div className="flex-1 p-6">
          <div className="mb-4 flex justify-between items-center">
            <div className="text-lg font-medium">材料列表</div>
            <div className="flex items-center space-x-4">
              <span className="text-amber-500 text-sm">⚠️ 3 文档无法被索引</span>
              <button className="px-4 py-2 bg-blue-100 text-blue-600 rounded text-sm">重试</button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded flex items-center text-sm">
                <span className="mr-1">+</span>
                添加文件
              </button>
            </div>
          </div>

          <div className="mb-6">
            <input
              type="text"
              placeholder="搜索"
              className="w-64 px-4 py-2 border rounded-lg bg-gray-50"
            />
          </div>

          <div className="bg-white rounded-lg shadow-sm">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b">
                  <th className="px-2 py-2 text-left font-medium">ID</th>
                  <th className="px-2 py-2 text-left font-medium">文件名</th>
                  <th className="px-2 py-2 text-left font-medium">类型</th>
                  <th className="px-2 py-2 text-left font-medium">大小</th>
                  <th className="px-2 py-2 text-left font-medium">段落数</th>
                  <th className="px-2 py-2 text-left font-medium">创建时间</th>
                  <th className="px-2 py-2 text-left font-medium">状态</th>
                  <th className="px-2 py-2 text-left font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((material) => (
                  <tr key={material._id} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2">{material._id}</td>
                    <td className="px-3 py-2">{material.title}</td>
                    <td className="px-3 py-2">{material.file_type}</td>
                    <td className="px-3 py-2">{(material.file_size / 1024).toFixed(1)}KB</td>
                    <td className="px-3 py-2">{material.segments.length}</td>
                    <td className="px-3 py-2">{new Date(material.created_at).toLocaleString()}</td>
                    <td className="px-3 py-2">
                      <span className={`${material.status === 'error' ? 'text-red-500' : 'text-green-500'}`}>
                        ● {material.status}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center space-x-2">
                        <div className="w-8 h-4 bg-gray-200 rounded-full relative">
                          <div className="absolute right-1 top-1 w-2 h-2 bg-white rounded-full"></div>
                        </div>
                        <button className="text-gray-400">...</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}