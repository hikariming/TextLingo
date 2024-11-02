const API_BASE_URL = 'http://127.0.0.1:5000/api'

const defaultHeaders = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type'
}

export const MaterialsAPI = {
  // 获取所有素材库
  getAll: async () => {
    const response = await fetch(`${API_BASE_URL}/materials-factory`, {
      method: 'GET',
      headers: defaultHeaders
    })
    if (!response.ok) throw new Error('Failed to fetch materials')
    return response.json()
  },

  // 创建新的素材库
  create: async (data) => {
    const response = await fetch(`${API_BASE_URL}/materials-factory`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || 'Failed to create material')
    }
    return response.json()
  },

  // 上传文件
  uploadFile: async (file, factoryId) => {
    const formData = new FormData()
    formData.append('factory_id', factoryId)
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/materials`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) throw new Error('Upload failed')
    return response.json()
  },

  // 获取单个素材的详细信息
  getById: async (materialId) => {
    const response = await fetch(`${API_BASE_URL}/materials/${materialId}`, {
      method: 'GET',
      headers: defaultHeaders
    })
    if (!response.ok) throw new Error('Failed to fetch material details')
    return response.json()
  },

  // 获取材料预览内容
  getPreview: async (materialId) => {
    const response = await fetch(`${API_BASE_URL}/materials/${materialId}/preview`, {
      method: 'GET',
      headers: defaultHeaders
    })
    if (!response.ok) throw new Error('Failed to fetch preview')
    return response.json()
  },

  // Add these new methods to MaterialsAPI object
  segmentMaterial: async (materialId, segmentationType) => {
    const response = await fetch(`${API_BASE_URL}/material-segments/segment-material/${materialId}`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ segmentation_type: segmentationType })
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || 'Failed to segment material')
    }
    return response.json()
  },

  getSegments: async (materialId, page = 1, perPage = 20) => {
    const response = await fetch(
      `${API_BASE_URL}/material-segments/material/${materialId}?page=${page}&per_page=${perPage}`, 
      {
        method: 'GET',
        headers: defaultHeaders
      }
    )
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || 'Failed to fetch segments')
    }
    return response.json()
  },
}