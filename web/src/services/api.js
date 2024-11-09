const API_BASE_URL = 'http://127.0.0.1:5000/api'

const defaultHeaders = {
  'Content-Type': 'application/json'
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

  // 开始翻译
  startTranslation: async (materialId, settings) => {
    const response = await fetch(`${API_BASE_URL}/materials/${materialId}/translate`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify(settings)
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || 'Failed to start translation')
    }
    return response.json()
  },

  // 更新材料设置
  updateMaterial: async (materialId, data) => {
    const response = await fetch(`${API_BASE_URL}/materials/${materialId}`, {
      method: 'PUT',
      headers: defaultHeaders,
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || 'Failed to update material')
    }
    return response.json()
  },

  // 获取所有材料列表
  getAllMaterials: async () => {
    const response = await fetch(`${API_BASE_URL}/materials`, {
      method: 'GET',
      headers: defaultHeaders
    })
    if (!response.ok) throw new Error('Failed to fetch materials')
    return response.json()
  },

  // 获取指定工厂的材料列表
  getMaterialsByFactory: async (factoryId) => {
    const response = await fetch(`${API_BASE_URL}/materials-factory/${factoryId}/materials`, {
      method: 'GET',
      headers: defaultHeaders
    })
    if (!response.ok) throw new Error('Failed to fetch factory materials')
    return response.json()
  },

  // 获取工厂详情
  getFactoryById: async (factoryId) => {
    const response = await fetch(`${API_BASE_URL}/materials-factory/${factoryId}`, {
      method: 'GET',
      headers: defaultHeaders
    })
    if (!response.ok) throw new Error('Failed to fetch factory details')
    return response.json()
  },

  // 删除材料
  deleteMaterial: async (materialId) => {
    const response = await fetch(`${API_BASE_URL}/materials/${materialId}`, {
      method: 'DELETE',
      headers: defaultHeaders
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || 'Failed to delete material')
    }
    return response.json()
  },

  // 修改 uploadText 方法
  uploadText: async (data) => {
    const response = await fetch(`${API_BASE_URL}/materials/text`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Upload failed')
    return response.json()
  },
}

// 在 api.js 中添加 VocabularyAPI
export const VocabularyAPI = {
  // 添加生词
  create: async (data) => {
    const response = await fetch(`${API_BASE_URL}/vocabularies`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || '添加生词失败')
    }
    return response.json()
  },

  // 获取生词列表
  getList: async (page = 1, perPage = 20) => {
    const response = await fetch(
      `${API_BASE_URL}/vocabularies?page=${page}&per_page=${perPage}`,
      {
        method: 'GET',
        headers: defaultHeaders
      }
    )
    if (!response.ok) throw new Error('获取生词列表失败')
    return response.json()
  },

  // 获取所有已收藏的单词
  getAllSavedWords: async () => {
    const response = await fetch(`${API_BASE_URL}/vocabularies`, {
      method: 'GET',
      headers: defaultHeaders
    })
    if (!response.ok) throw new Error('获取收藏单词失败')
    return response.json()
  },

  // 删除收藏的单词
  delete: async (vocabularyId) => {
    const response = await fetch(`${API_BASE_URL}/vocabularies/${vocabularyId}`, {
      method: 'DELETE',
      headers: defaultHeaders
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || '取消收藏失败')
    }
    return response.json()
  },

  // 批量检查单词是否已收藏
  checkSavedWords: async (words) => {
    const response = await fetch(`${API_BASE_URL}/vocabularies/check`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ words })
    })
    if (!response.ok) throw new Error('检查收藏状态失败')
    return response.json()
  }
}

export const GrammarAPI = {
  // 添加语法点
  create: async (data) => {
    const response = await fetch(`${API_BASE_URL}/grammars`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || '添加语法点失败')
    }
    return response.json()
  },

  // 获取语法点列表
  getList: async (page = 1, perPage = 20) => {
    const response = await fetch(
      `${API_BASE_URL}/grammars?page=${page}&per_page=${perPage}`,
      {
        method: 'GET',
        headers: defaultHeaders
      }
    )
    if (!response.ok) throw new Error('获取语法点列表失败')
    return response.json()
  },

  // 删除语法点
  delete: async (grammarId) => {
    const response = await fetch(`${API_BASE_URL}/grammars/${grammarId}`, {
      method: 'DELETE',
      headers: defaultHeaders
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || '删除语法点失败')
    }
    return response.json()
  },

  // 批量检查语法点是否已保存
  checkSavedGrammars: async (names) => {
    const response = await fetch(`${API_BASE_URL}/grammars/check`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ names })
    })
    if (!response.ok) throw new Error('检查语法点状态失败')
    return response.json()
  }
}

export const SettingAPI = {
  // 获取配置
  getConfig: async () => {
    const response = await fetch(`${API_BASE_URL}/setting`, {
      method: 'GET',
      headers: defaultHeaders
    })
    if (!response.ok) throw new Error('获取配置失败')
    return response.json()
  },

  // 更新配置
  updateConfig: async (config) => {
    const response = await fetch(`${API_BASE_URL}/setting`, {
      method: 'PUT',
      headers: defaultHeaders,
      body: JSON.stringify(config)
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || '更新配置失败')
    }
    return response.json()
  },

  // 测试LLM连接
  testLLMConnection: async () => {
    const response = await fetch(`${API_BASE_URL}/setting/test-llm`, {
      method: 'POST',
      headers: defaultHeaders
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.message || '测试连接失败')
    }
    return data
  }
}