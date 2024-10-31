'use client'
import { useState } from 'react'
import Link from 'next/link'

export default function MaterialManagement() {
  const [materials, setMaterials] = useState([
    {
      id: 1,
      name: '反转、暴击！这些视频在海外网站火了，老外来过上海后感叹："中国和我们想象的太不一样".pdf',
      size: '4.4k',
      citations: 0,
      uploadTime: '2024-08-02 09:25',
      status: '错误'
    },
    // ... 可以添加更多初始数据
  ])

  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex flex-1">
        {/* 左侧导航栏 */}
        <div className="w-64 border-r bg-white">
          <div className="p-4">
            <Link href="/" className="text-blue-600 hover:text-blue-700 flex items-center">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              素材库管理
            </Link>
          </div>
        </div>

        {/* 右侧内容区 */}
        <div className="flex-1 p-6">
          <div className="mb-4 flex justify-between items-center">
            <div className="text-xl font-medium">文档</div>
            <div className="flex items-center space-x-4">
              <span className="text-amber-500">⚠️ 3 文档无法被索引</span>
              <button className="px-4 py-2 bg-blue-100 text-blue-600 rounded">重试</button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded flex items-center">
                <span className="mr-1">+</span>
                添加文件
              </button>
            </div>
          </div>

          {/* 搜索框 */}
          <div className="mb-6">
            <input
              type="text"
              placeholder="搜索"
              className="w-64 px-4 py-2 border rounded-lg bg-gray-50"
            />
          </div>

          {/* 文件列表 */}
          <div className="bg-white rounded-lg">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="px-4 py-3 text-left">#</th>
                  <th className="px-4 py-3 text-left">文件名</th>
                  <th className="px-4 py-3 text-left">字符数</th>
                  <th className="px-4 py-3 text-left">召回次数</th>
                  <th className="px-4 py-3 text-left">上传时间</th>
                  <th className="px-4 py-3 text-left">状态</th>
                  <th className="px-4 py-3 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((material) => (
                  <tr key={material.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3">{material.id}</td>
                    <td className="px-4 py-3">{material.name}</td>
                    <td className="px-4 py-3">{material.size}</td>
                    <td className="px-4 py-3">{material.citations}</td>
                    <td className="px-4 py-3">{material.uploadTime}</td>
                    <td className="px-4 py-3">
                      <span className="text-red-500">● {material.status}</span>
                    </td>
                    <td className="px-4 py-3">
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