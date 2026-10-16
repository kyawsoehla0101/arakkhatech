/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../../**/*.{html,py,js}', // This should match the @source directive in styles.css
  ],
  theme: {
    extend: {
      colors: {
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        accent: 'var(--color-accent)',
        'text-dark': 'var(--color-text-dark)',
        'text-light': 'var(--color-text-light)',
        'background-light': 'var(--color-background-light)',
        'background-dark': 'var(--color-background-dark)',
      },
    },
  },
  plugins: [],
}