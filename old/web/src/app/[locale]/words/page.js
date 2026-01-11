'use client'

import { useEffect, useState } from 'react'
import Navbar from '../../components/navigation/Navbar'
import WordList from './components/Wordlist'
import { VocabularyAPI } from '../../../services/api'
import Link from 'next/link'

export default function Component() {
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total_review: 0,
    reviewed_count: 0,
    remaining_count: 0,
    accuracy_rate: 0
  });
  const [animationReady, setAnimationReady] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [wordsResponse, statsResponse] = await Promise.all([
          VocabularyAPI.getAllSavedWords(),
          VocabularyAPI.getReviewStats()
        ]);
        
        const formattedWords = wordsResponse.data.items.map(item => ({
          id: item._id,
          word: item.word,
          translation: item.meaning,
          reading: item.reading,
          sourceSegmentId: item.source_segment_id
        }));
        
        setWords(formattedWords);
        setStats(statsResponse.data);
        setTimeout(() => setAnimationReady(true), 100);
      } catch (error) {
        console.error('获取数据失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <>
      <Navbar />
      <div className="bg-slate-100 min-h-screen pt-20">
        <div className="container mx-auto p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <Link href="/zh/words/learn" className="block">
            <h1 className="text-2xl font-bold mb-6 text-black">词汇背诵</h1>
              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow">
                <h2 className="text-xl font-bold mb-4">今日学习</h2>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">待复习单词</span>
                  <span className="text-blue-600 font-medium">
                    {stats.remaining_count} 个
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-700"
                    style={{ 
                      width: animationReady ? `${(stats.reviewed_count / stats.total_review) * 100}%` : '0%'
                    }}
                  ></div>
                </div>
              </div>
            </Link>
          </div>

          <h1 className="text-2xl font-bold mb-6 text-black">词汇收藏</h1>
          
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