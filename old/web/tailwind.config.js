/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class', // 改为 'class' 或 'media'
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        }
      },
      animation: {
        'fade-in': 'fade-in 0.3s ease-out'
      }
    },
  },
  plugins: [],
};
