'use client'

import { useTranslations } from 'next-intl'
import { useEffect, useState } from 'react'
import { SettingAPI } from '@/services/api'

export default function VocabularySettings() {
    const t = useTranslations('app.setting')
    const [config, setConfig] = useState({
        daily_review_limit: 20
    })
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        loadConfig()
    }, [])

    const loadConfig = async () => {
        try {
            const data = await SettingAPI.getVocabularyConfig()
            setConfig(data)
        } catch (error) {
            console.error('加载配置失败:', error)
        }
    }

    const handleUpdateConfig = async (value) => {
        setLoading(true)
        try {
            await SettingAPI.updateVocabularyConfig({
                daily_review_limit: value
            })
            setConfig(prev => ({
                ...prev,
                daily_review_limit: value
            }))
        } catch (error) {
            console.error('更新配置失败:', error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">{t('vocabularySettings')}</h2>
            
            <div>
                <label className="block text-sm font-medium mb-2">{t('dailyTarget')}</label>
                <input
                    type="number"
                    min="1"
                    max="100"
                    value={config.daily_review_limit}
                    onChange={(e) => handleUpdateConfig(parseInt(e.target.value))}
                    disabled={loading}
                    className="w-full p-2 border rounded-md"
                />
            </div>
        </div>
    )
} 