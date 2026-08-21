/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4f46e5',
          dark: '#3730a3',
          light: '#eef2ff',
        },
      },
      boxShadow: {
        soft: '0 10px 35px -15px rgba(15, 23, 42, 0.18)',
      },
    },
  },
  plugins: [],
}
