'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import Navbar from '../../../../components/navigation/Navbar'
import { MaterialsAPI } from '../../../../../services/api'
import { useParams, useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'

export default function MaterialManagement() {
  const params = useParams()
  const router = useRouter()
  const [factory, setFactory] = useState(null)
  const [materials, setMaterials] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)
  const t = useTranslations('app')

  const filteredMaterials = materials.filter(material => {
    const searchLower = searchQuery.toLowerCase()
    return (
      material.original_filename?.toLowerCase().includes(searchLower) ||
      material.title?.toLowerCase().includes(searchLower) ||
      material.file_type?.toLowerCase().includes(searchLower) ||
      material.status?.toLowerCase().includes(searchLower)
    )
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('Fetching data for factory ID:', params.id)
        
        const [factoryData, materialsData] = await Promise.all([
          MaterialsAPI.getFactoryById(params.id),
          MaterialsAPI.getMaterialsByFactory(params.id)
        ])
        
        console.log('Factory data:', factoryData)
        console.log('Materials data:', materialsData)
        
        setFactory(factoryData)
        setMaterials(materialsData.materials || [])
      } catch (error) {
        console.error('Error details:', {
          message: error.message,
          stack: error.stack,
          response: error.response
        })
        setMaterials([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [params.id])

  useEffect(() => {
    console.log('Current state:', {
      factory,
      materials,
      loading,
      paramsId: params.id
    })
  }, [factory, materials, loading, params.id])

  const handleDelete = async (materialId) => {
    if (!confirm('确定要删除这个材料吗？')) return
    
    try {
      setDeleteLoading(true)
      await MaterialsAPI.deleteMaterial(materialId)
      // 更新列表，移除已删除的材料
      setMaterials(materials.filter(m => m._id !== materialId))
    } catch (error) {
      console.error('删除失败:', error)
      alert('删除失败: ' + error.message)
    } finally {
      setDeleteLoading(false)
    }
  }

  const handleResegment = (materialId) => {
    router.push(`/${t('locale')}/material/create?materialId=${materialId}&step=2`)
  }

  if (loading || !factory) {
    return <div>Loading...</div>
  }

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
              <Link href={`/${t('locale')}/material/create?factoryId=${params.id}`}>
                <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                  添加新阅读材料
                </button>
              </Link>
            </div>

            <div className="border-t pt-4">
              <h3 className="text-sm font-medium mb-2">快速统计</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-xs text-gray-500">处理中</div>
                  <div className="text-lg font-medium text-gray-400">开发中</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-xs text-gray-500">已完成</div>
                  <div className="text-lg font-medium text-gray-400">开发中</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-xs text-gray-500">出错</div>
                  <div className="text-lg font-medium text-gray-400">开发中</div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-xs text-gray-500">总字数</div>
                  <div className="text-lg font-medium text-gray-400">开发中</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 主要内容区域：材料列表 */}
        <div className="flex-1 p-6">
          <div className="mb-4 flex justify-between items-center">
            <div className="text-lg font-medium">材料列表</div>
          </div>

          <div className="mb-6">
            <input
              type="text"
              placeholder="搜索"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 px-4 py-2 border rounded-lg bg-gray-50"
            />
          </div>

          <div className="bg-white rounded-lg shadow-sm">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b">
                  <th className="px-2 py-2 text-left font-medium">文件名</th>
                  <th className="px-2 py-2 text-left font-medium">类型</th>
                  <th className="px-2 py-2 text-left font-medium">大小</th>
                  <th className="px-2 py-2 text-left font-medium">创建时间</th>
                  <th className="px-2 py-2 text-left font-medium">状态</th>
                  <th className="px-2 py-2 text-left font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {Array.isArray(filteredMaterials) && filteredMaterials.length > 0 ? (
                  filteredMaterials.map((material) => (
                    <tr key={material._id} className="border-b hover:bg-gray-50">
                      <td className="px-3 py-2">{material.original_filename || material.title}</td>
                      <td className="px-3 py-2">{material.file_type}</td>
                      <td className="px-3 py-2">{(material.file_size / 1024).toFixed(1)}KB</td>
                      <td className="px-3 py-2">{new Date(material.created_at).toLocaleString()}</td>
                      <td className="px-3 py-2">
                        <span className={`${
                          material.status === 'translation_failed' ? 'text-red-500' :  // 失败状态 - 红色
                          material.status === 'translating' ? 'text-amber-500' :       // 翻译中 - 琥珀色
                          material.status === 'pending_segmentation' ? 'text-blue-500' : // 待分段 - 蓝色
                          material.status === 'segmented' ? 'text-purple-500' :        // 已分段 - 紫色
                          material.status === 'translated' ? 'text-green-500' :        // 已翻译 - 绿色
                          'text-gray-500'                                             // 默认颜色
                        }`}>
                          ● {material.status}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center space-x-2">
                          <button 
                            onClick={() => handleDelete(material._id)}
                            disabled={deleteLoading}
                            className="text-red-500 hover:text-red-700 disabled:opacity-50"
                          >
                            删除
                          </button>
                          <button 
                            onClick={() => handleResegment(material._id)}
                            className="text-blue-500 hover:text-blue-700"
                          >
                            重新分段
                          </button>
                          <button className="text-gray-400">...</button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="6" className="px-3 py-4 text-center text-gray-500">
                      暂无材料数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}