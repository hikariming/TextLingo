'use client'

import React, { useState } from 'react'
import AIExplanation from './components/AIExplanation'
import ReadingMaterials from './components/ReadingMaterials'

export default function TranslationLearningPage() {
  const [selectedMaterial, setSelectedMaterial] = useState('material1')
  const [showTranslation, setShowTranslation] = useState(false)
  const [selectedSentence, setSelectedSentence] = useState(null)

  const readingMaterials = [
    { id: 'material1', title: '満ちてゆく 藤井风' },
    { id: 'material2', title: 'China\'s giant economy faces an equally giant crisis of confidence—and a growing deficit of accurate information is only making things worse.' },
  ]

  const content = {
    material1: [
      {
        original: "走り出した午後も",
        translation: "开始奔跑的下午也...",
        isNewParagraph: true,
        grammar: [
          { name: "走り出す", explanation: "复合动词，由「走る」（跑）和「出す」（开始）组成，表示「开始跑」" },
          { name: "走り出した", explanation: "「走り出す」的た形，表示过去完成的动作" },
          { name: "午後", explanation: "名词，表示「下午」" },
          { name: "も", explanation: "助词，表示「也」，用于强调或添加信息" }
        ],
        vocabulary: [
          { word: "走り出す", reading: "はしりだす", meaning: "开始跑" },
          { word: "午後", reading: "ごご", meaning: "下午" }
        ]
      },
      {
        original: "重ね合う日々も",
        translation: "重叠交织的日子也...",
        isNewParagraph: true,
        grammar: [
          { name: "重ね合う", explanation: "复合动词，由「重ねる」（叠加）和「合う」（相互）组成，表示相互叠加或重叠的意思。这里使用了连体形" },
          { name: "日々", explanation: "名词，表示「日子」或「时光」" },
          { name: "も", explanation: "助词，表示「也」或「即使」的意思，用于强调或包含" }
        ],
        vocabulary: [
          { word: "重ね合う", reading: "かさねあう", meaning: "重叠，叠加" },
          { word: "日々", reading: "ひび", meaning: "日子，时光" }
        ]
      },
      {
        original: "避けがたく全て終わりが来る",
        translation: "难以避免地，一切都将迎来终结。",
        isNewParagraph: true,
        grammar: [
          { name: "避けがたく", explanation: "容词「避けがたい」的连用形，表示「难以避免」" },
          { name: "全て", explanation: "副词，表示「全部、一切」" },
          { name: "終わり", explanation: "名词，意为「结束」" },
          { name: "が", explanation: "主格助词，标示主语" },
          { name: "来る", explanation: "动词，表示「来到」，这里用于表示抽象的「发生」" }
        ],
        vocabulary: [
          { word: "避けがたい", reading: "さけがたい", meaning: "难以避免的" },
          { word: "全て", reading: "すべて", meaning: "全部、一切" },
          { word: "終わり", reading: "おわり", meaning: "结束" }
        ]
      },
      {
        original: "あの日のきらめきも",
        translation: "那一天的闪耀光芒也...",
        isNewParagraph: true,
        grammar: [
          { name: "あの", explanation: "指示形容词，表示「那个」" },
          { name: "日", explanation: "名词，表示「日子」" },
          { name: "の", explanation: "格助词，表示所属关系" },
          { name: "きらめき", explanation: "名词，由动词「きらめく」（闪耀）转化而来" },
          { name: "も", explanation: "助词，表示「也」，用于强调或列举" }
        ],
        vocabulary: [
          { word: "あの", reading: "あの", meaning: "那个" },
          { word: "日", reading: "ひ", meaning: "日子" },
          { word: "きらめき", reading: "きらめき", meaning: "闪耀，光芒" }
        ]
      },
      {
        original: "淡いときめきも",
        translation: "淡淡的心动也...",
        isNewParagraph: true,
        grammar: [
          { name: "淡い", explanation: "形容词，表示「淡薄的、浅淡的」" },
          { name: "ときめき", explanation: "名词，意为「心跳加速、心动」" },
          { name: "も", explanation: "助词，表示「也」，用于增加或强调" }
        ],
        vocabulary: [
          { word: "淡い", reading: "あわい", meaning: "淡薄的、浅淡的" },
          { word: "ときめき", reading: "ときめき", meaning: "心跳加速、心动" }
        ]
      },
      {
        original: "あれもこれもどこか置いてくる",
        translation: "把这个那个都放在某处后再回来。",
        isNewParagraph: true,
        grammar: [
          { name: "あれも", explanation: "并列结构，表示「这个也...那个也...」" },
          { name: "も", explanation: "助词，表示强调和包含" },
          { name: "どこか", explanation: "不定代词，表示「某处」" },
          { name: "置いてくる", explanation: "复合动词，由「置く」（放置）和「くる」（来）组成" }
        ],
        vocabulary: [
          { word: "あれ", reading: "あれ", meaning: "那个" },
          { word: "これ", reading: "これ", meaning: "这个" },
          { word: "どこか", reading: "どこか", meaning: "某处" },
          { word: "置く", reading: "おく", meaning: "放置" },
          { word: "くる", reading: "くる", meaning: "来" }
        ]
      }
    ],
    material2: [
      {
        original: "333333",
        translation: "中国庞大的经济面临着同样巨大的信心危机，而且不断增长的准确信息缺失只会让情况变得更糟。",
        isNewParagraph: false,
        grammar: [
          { name: "这是一个复合句", explanation: "使用破折号连接两个相关的陈述" },
          { name: "giant作为形容词表示'巨大的'", explanation: "" },
          { name: "deficit of 表示'缺乏'", explanation: "" }
        ],
        vocabulary: [
          { word: "giant", meaning: "巨大的" },
          { word: "confidence", meaning: "信心" },
          { word: "deficit", meaning: "缺乏，赤字" }
        ]
      },
      {
        original: "China's giant economy faces an equally giant crisis of confidence—and a growing deficit of accurate information is only making things worse.111111111111111",
        translation: "中国庞大的经济面临着同样巨大的信心危机，而且不断增长的准确信息缺失只会让情况变得更糟。",
        isNewParagraph: true,
        grammar: [
          { name: "这是一个复合句", explanation: "使用破折号连接两个相关的陈述" },
          { name: "giant作为形容词表示'巨大的'", explanation: "" },
          { name: "deficit of 表示'缺乏'", explanation: "" }
        ],
        vocabulary: [
          { word: "giant", meaning: "巨大的" },
          { word: "confidence", meaning: "信心" },
          { word: "deficit", meaning: "缺乏，赤字" }
        ]
      },
      {
        original: "Even as the country wrestles with a property crash, the services sector slowed by one measure in August.",
        translation: "即使在国家正在应对房地产崩盘的同时，服务业部门在8月份的某项指标上也出现了放缓。",
        isNewParagraph: false,
        grammar: [
          { name: "Even as 表示让步关系", explanation: "" },
          { name: "wrestle with 表示'与...搏斗、应对'", explanation: "" }
        ],
        vocabulary: [
          { word: "wrestle", meaning: "搏斗，应对" },
          { word: "property crash", meaning: "房地产崩盘" }
        ]
      },
      {
        original: "Even a11s the country wrestles with a property crash, the services sector slowed by one measure in August.",
        translation: "即使在国家正在应对房地产崩盘的同时，服务业部门在8月份的某项指标上也出现了放缓。",
        isNewParagraph: false,
        grammar: [
          { name: "Even as 表示让步关系", explanation: "" },
          { name: "wrestle with 表示'与...搏斗、应对'", explanation: "" }
        ],
        vocabulary: [
          { word: "wrestle", meaning: "搏斗，应对" },
          { word: "property crash", meaning: "房地产崩盘" }
        ]
      },
      {
        original: "Even a122321s the country wrestles with a property crash, the services sector slowed by one measure in August.",
        translation: "即使在国家正在应对房地产崩盘的同时，服务业部门在8月份的某项指标上也出现了放缓。",
        isNewParagraph: true,
        grammar: [
          { name: "Even as 表示让步关系", explanation: "" },
          { name: "wrestle with 表示'与...搏斗、应对'", explanation: "" }
        ],
        vocabulary: [
          { word: "wrestle", meaning: "搏斗，应对" },
          { word: "property crash", meaning: "房地产崩盘" }
        ]
      },
      {
        original: "Even a1221321s the country wrestles with a property crash, the services sector slowed by one measure in August.",
        translation: "即使在国家正在应对房地产崩盘的同时，服务业部门在8月份的某项指标上也出现了放缓。",
        isNewParagraph: false,
        grammar: [
          { name: "Even as 表示让步关系", explanation: "" },
          { name: "wrestle with 表示'与...搏斗、应对'", explanation: "" }
        ],
        vocabulary: [
          { word: "wrestle", meaning: "搏斗，应对" },
          { word: "property crash", meaning: "房地产崩盘" }
        ]
      }
    ]
  }

  return (
    <div className="flex h-screen bg-white text-gray-900">
      {/* Left Navigation */}
      <ReadingMaterials 
        readingMaterials={readingMaterials}
        selectedMaterial={selectedMaterial}
        onMaterialSelect={setSelectedMaterial}
      />

      {/* Middle Reading Area */}
      <main className="flex-1 overflow-auto p-6 bg-white">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            {readingMaterials.find(m => m.id === selectedMaterial)?.title}
          </h1>
          <div className="flex items-center space-x-2">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                className="sr-only peer"
                checked={showTranslation}
                onChange={(e) => setShowTranslation(e.target.checked)}
              />
              <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              <span className="ml-3 text-sm font-medium text-gray-900">Show Translation</span>
            </label>
          </div>
        </div>
        <div>
          {(() => {
            const sentences = content[selectedMaterial];
            
            // 先把句子按段落分组
            const paragraphs = [];
            let currentParagraph = [];

            sentences.forEach((sentence) => {
              if (sentence.isNewParagraph && currentParagraph.length > 0) {
                console.log(sentence.original);
                // 如果是新段落且当前段落不为空，保存当前段落并开始新段落
                paragraphs.push(currentParagraph);
                currentParagraph = [sentence];
              } else {
                // 否则添加到当前段落
                currentParagraph.push(sentence);
              }
            });

            // 添加最后一个段落
            if (currentParagraph.length > 0) {
              paragraphs.push(currentParagraph);
            }

            // 检查数组长度和第一段的存在性，然后再进行合并操作
            if (paragraphs.length > 1 && 
                paragraphs[0]?.length > 0 && 
                paragraphs[0][0]?.isNewParagraph === false) {
              paragraphs[0] = [...paragraphs[0], ...paragraphs[1]];
              paragraphs.splice(1, 1);
            }

            console.log(paragraphs);

            return paragraphs.map((paragraph, paraIndex) => (
              <div key={paraIndex} className={`${paraIndex > 0 ? 'mt-4' : ''}`}>
                {paragraph.map((sentence, sentIndex) => (
                  <span key={sentIndex} className="inline">
                    <span
                      className={`border-b-2 ${
                        selectedSentence === sentence.original 
                          ? 'border-blue-400' 
                          : 'border-transparent hover:border-gray-200'
                      }`}
                      onClick={() => setSelectedSentence(sentence.original)}
                    >
                      {sentence.original}
                    </span>
                    {showTranslation && (
                      <div className="mt-2 text-gray-600">
                        {sentence.translation}
                      </div>
                    )}
                  </span>
                ))}
              </div>
            ));
          })()}
        </div>
      </main>

      {/* Right AI Explanation */}
      <AIExplanation 
        selectedSentence={selectedSentence}
        content={content}
        selectedMaterial={selectedMaterial}
      />
    </div>
  )
}