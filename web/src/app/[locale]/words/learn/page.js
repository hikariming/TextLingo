'use client'

import { useEffect, useState } from 'react'
import { VocabularyAPI } from '@/services/api'

export default function LearnPage() {
    const [currentWord, setCurrentWord] = useState(null)
    const [showTranslation, setShowTranslation] = useState(false)
    const [loading, setLoading] = useState(true)
    const [wordSources, setWordSources] = useState(null)
    const [loadingSources, setLoadingSources] = useState(false)
    const [stats, setStats] = useState({
        total_review: 0,
        reviewed_count: 0,
        remaining_count: 0,
        accuracy_rate: 0
    })

    // 加载统计信息
    const loadStats = async () => {
        try {
            const response = await VocabularyAPI.getReviewStats()
            if (response.data) {
                setStats(response.data)
            }
        } catch (error) {
            console.error('加载统计信息失败:', error)
        }
    }

    // 加载下一个单词
    const loadNextWord = async () => {
        try {
            setLoading(true)
            const response = await VocabularyAPI.getNextReviewWord()
            if (response.data) {
                setCurrentWord(response.data)
            } else {
                setCurrentWord(null) // 没有更多单词了
            }
        } catch (error) {
            console.error('加载单词失败:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadStats()
        loadNextWord()
    }, [])

    const handleKnown = async () => {
        if (!currentWord) return
        try {
            await VocabularyAPI.submitReviewResult(currentWord._id, 'remembered')
            await loadStats()
            await loadNextWord()
            setShowTranslation(false)
        } catch (error) {
            console.error('提交结果失败:', error)
        }
    }

    const handleUnknown = async () => {
        if (!currentWord) return
        setShowTranslation(true)
        
        // 加载相关例句
        setLoadingSources(true)
        try {
            const response = await VocabularyAPI.getSources(currentWord._id)
            setWordSources(response.data.sources)
        } catch (error) {
            console.error('加载例句失败:', error)
        } finally {
            setLoadingSources(false)
        }
    }

    const handleNext = async () => {
        if (!currentWord) return
        try {
            await VocabularyAPI.submitReviewResult(currentWord._id, 'forgotten')
            await loadStats()
            await loadNextWord()
            setShowTranslation(false)
        } catch (error) {
            console.error('提交结果失败:', error)
        }
    }

    const handleMastered = async () => {
        if (!currentWord) return
        try {
            await VocabularyAPI.markWordMastered(currentWord._id)
            await loadStats()
            await loadNextWord()
            setShowTranslation(false)
        } catch (error) {
            console.error('标记已掌握失败:', error)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-lg">加载中...</div>
            </div>
        )
    }

    if (!currentWord) {
        return (
            <div className="container mx-auto px-4 py-8 max-w-3xl">
                <div className="text-center">
                    <h2 className="text-2xl font-bold mb-4">今日学习完成！</h2>
                    <p className="text-gray-600 mb-4">
                        复习进度: {stats.reviewed_count}/{stats.total_review}
                        <br />
                        正确率: {stats.accuracy_rate}%
                    </p>
                    <button
                        onClick={loadNextWord}
                        className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                    >
                        刷新
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl">
            {/* 进度展示 */}
            <div className="mb-8">
                <div className="flex justify-between mb-2 text-gray-600">
                    <span>今日学习进度</span>
                    <span>{stats.reviewed_count} / {stats.total_review}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                    <div 
                        className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                        style={{ width: `${(stats.reviewed_count / stats.total_review) * 100}%` }}
                    ></div>
                </div>
            </div>

            {/* 单词卡片 */}
            <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
                <div className="text-center">
                    <h2 className="text-4xl font-bold mb-6">{currentWord.word}</h2>
                    {currentWord.reading && (
                        <p className="text-gray-500 mb-4">{currentWord.reading}</p>
                    )}

                    {showTranslation && (
                        <div className="space-y-6 mt-8">
                            <div>
                                <h3 className="text-xl text-gray-800 font-medium mb-2">释义</h3>
                                <p className="text-lg text-gray-600">{currentWord.meaning}</p>
                            </div>

                            {/* 添加例句显示部分 */}
                            <div className="mt-6">
                                <h3 className="text-xl text-gray-800 font-medium mb-2">相关例句</h3>
                                {loadingSources ? (
                                    <p className="text-gray-500">加载中...</p>
                                ) : wordSources?.length > 0 ? (
                                    <div className="space-y-4">
                                        {wordSources.map((source, index) => (
                                            <div key={index} className="text-left bg-gray-50 p-4 rounded-lg">
                                                <p className="text-gray-800">{source.original}</p>
                                                <p className="text-gray-600 mt-2">{source.translation}</p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-gray-500">暂无相关例句</p>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-center space-x-6">
                {!showTranslation ? (
                    <>
                        <button
                            onClick={handleUnknown}
                            className="px-8 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                        >
                            不认识
                        </button>
                        <button
                            onClick={handleKnown}
                            className="px-8 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                        >
                            认识
                        </button>
                        <button
                            onClick={handleMastered}
                            className="px-8 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
                        >
                            已掌握
                        </button>
                    </>
                ) : (
                    <button
                        onClick={handleNext}
                        className="px-12 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    >
                        下一个
                    </button>
                )}
            </div>
        </div>
    )
}
