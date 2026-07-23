/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'deep-plum': '#3B1F3A',
        'plum': '#6B3A6B',
        'gold': '#C9A84C',
        'cream': '#FAF6EF',
      },
      fontFamily: {
        display: ['Fraunces', 'serif'],
        body: ['Jost', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
