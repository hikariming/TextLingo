'use client';

import React from "react";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";

const LanguageSwitcher = () => {
  const router = useRouter();
  const pathname = usePathname();

  const options = [
    { language: "中文", code: "zh" },
    { language: "English", code: "en" },
    { language: "日本語", code: "jp" },
  ];

  const setOption = (option) => {
    router.push(`/${option.code}`);
  };

  return (
    <div className="relative inline-block text-left">
      <select 
        className="block w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        onChange={(e) => setOption(options[e.target.value])}
        value={options.findIndex(opt => pathname === `/${opt.code}`)}
      >
        {options.map((option, index) => (
          <option key={index} value={index}>
            {option.language}
          </option>
        ))}
      </select>
    </div>
  );
};

export default LanguageSwitcher;
