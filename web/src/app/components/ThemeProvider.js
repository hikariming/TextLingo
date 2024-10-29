'use client'

import { useEffect } from 'react'

export default function ThemeProvider({ children }) {
  useEffect(() => {
    document.documentElement.classList.remove('dark')
    document.documentElement.classList.add('light')
    
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      document.documentElement.classList.remove('dark')
      document.documentElement.classList.add('light')
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  return children
} 