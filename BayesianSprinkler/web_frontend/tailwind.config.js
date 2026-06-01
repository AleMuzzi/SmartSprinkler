/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        smart: {
          green: '#4CAF50',
          blue: '#2196F3',
          red: '#F44336',
          orange: '#FF9800',
          dark: '#2D3748',
          gray: '#718096',
          light: '#F5F7FA',
        },
      },
    },
  },
  plugins: [],
}