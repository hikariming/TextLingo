'use client'

import { useTranslations } from 'next-intl'

export default function VocabularySettings({ config, onUpdateConfig }) {
  const t = useTranslations('app.setting')

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold mb-4">{t('vocabularySettings')}</h2>
      
      <div>
        <label className="block text-sm font-medium mb-2">{t('dailyTarget')}</label>
        <input
          type="number"
          min="1"
          max="100"
          value={config.daily_words_target || 20}
          onChange={(e) => onUpdateConfig({...config, daily_words_target: parseInt(e.target.value)})}
          className="w-full p-2 border rounded-md"
        />
      </div>

      

    </div>
  )
} 