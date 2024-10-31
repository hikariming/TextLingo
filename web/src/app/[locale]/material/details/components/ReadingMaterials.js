'use client'

import { BookOpenIcon } from '@heroicons/react/24/outline'

export default function ReadingMaterials({ 
  readingMaterials, 
  selectedMaterial, 
  onMaterialSelect 
}) {
  return (
    <nav className="w-64 border-r border-neutral-200 bg-slate-50 p-4">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Reading Materials</h2>
      <ul>
        {readingMaterials.map((material) => (
          <li key={material.id} className="mb-2">
            <button
              className={`w-full flex items-center px-4 py-2 rounded-full text-left transition-colors
                ${selectedMaterial === material.id 
                  ? 'bg-white text-blue-600 shadow-md' 
                  : 'text-gray-900 hover:text-gray-600'
                }`}
              onClick={() => onMaterialSelect(material.id)}
              title={material.title}
            >
              <BookOpenIcon className={`flex-shrink-0 mr-2 h-4 w-4 ${
                selectedMaterial === material.id ? 'text-blue-600' : ''
              }`} />
              <span className="truncate">
                {material.title}
              </span>
              {selectedMaterial === material.id && (
                <div className="absolute -bottom-[1px] left-2 right-2 h-[2px] bg-gradient-to-r from-blue-400/0 via-blue-400/70 to-blue-400/0"></div>
              )}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
