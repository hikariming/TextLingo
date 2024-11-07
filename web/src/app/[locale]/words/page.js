'use client'

import { useEffect, useState } from 'react'
import Navbar from '../../components/navigation/Navbar'
import WordList from './components/Wordlist'
import { VocabularyAPI } from '../../../services/api'

export default function Component() {
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWords = async () => {
      try {
        const response = await VocabularyAPI.getAllSavedWords();
        const formattedWords = response.data.items.map(item => ({
          id: item._id,
          word: item.word,
          translation: item.meaning,
          reading: item.reading,
          sourceSegmentId: item.source_segment_id
        }));
        setWords(formattedWords);
      } catch (error) {
        console.error('获取词汇列表失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchWords();
  }, []);

  return (
    <>
      <Navbar />
      <div className="bg-slate-100 min-h-screen pt-20">
        <div className="container mx-auto p-4">
          <h1 className="text-2xl font-bold mb-6 text-black">词汇收藏</h1>
          <p className="text-gray-600 mb-4">背单词、复习、做题等功能还在开发中...</p>
          
          {loading ? (
            <div>加载中...</div>
          ) : (
            <WordList initialWords={words} />
          )}
        </div>
      </div>
    </>
  )
}