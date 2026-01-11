'use client'

import { useState, useEffect } from 'react'
import Navbar from '../../components/navigation/Navbar'
import KnowledgeContent from './components/KnowledgeContent'
import { GrammarAPI } from '../../../services/api'

export default function KnowledgePage() {
  const [savedGrammars, setSavedGrammars] = useState([])

  useEffect(() => {
    const fetchGrammars = async () => {
      try {
        const response = await GrammarAPI.getList()
        // 从返回的数据结构中正确提取 items 数组
        const grammars = response.data?.items || []
        
        const formattedGrammars = grammars.map(grammar => ({
          id: grammar._id,
          type: 'grammar',
          title: grammar.name,
          explanation: grammar.explanation,
          createdAt: grammar.created_at,
          sourceSegmentId: grammar.source_segment_id
        }))
        
        setSavedGrammars(formattedGrammars)
      } catch (error) {
        console.error('获取语法点失败:', error)
      }
    }

    fetchGrammars()
  }, [])

  return (
    <>
      <Navbar />
      <div className="bg-slate-100 min-h-screen pt-16">
        <div className="container mx-auto p-4">
          <KnowledgeContent initialGrammars={savedGrammars} />
        </div>
      </div>
    </>
  )
}