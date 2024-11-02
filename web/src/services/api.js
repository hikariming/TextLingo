const API_BASE_URL = 'http://127.0.0.1:5000/api'

export const MaterialsAPI = {
  // 获取所有素材库
  getAll: async () => {
    const response = await fetch(`${API_BASE_URL}/materials-factory`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    if (!response.ok) throw new Error('Failed to fetch materials')
    return response.json()
  },

  // 创建新的素材库
  create: async (data) => {
    const response = await fetch(`${API_BASE_URL}/materials-factory`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || 'Failed to create material')
    }
    return response.json()
  },

  // 上传文件
  uploadFile: async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/materials`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) throw new Error('Upload failed')
    return response.json()
  }
}