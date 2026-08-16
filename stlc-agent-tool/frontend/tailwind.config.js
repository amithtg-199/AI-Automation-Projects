/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        main: 'var(--bg-main)',
        card: 'var(--bg-card)',
        elevated: 'var(--bg-elevated)',
        border: 'var(--border)',
        primary: {
          DEFAULT: 'var(--primary)',
          hover: 'var(--primary-hover)',
          foreground: '#ffffff'
        },
        success: 'var(--success)',
        fail: 'var(--fail)',
        warning: 'var(--warning)',
        info: 'var(--info)',
      },
      textColor: {
        primary: 'var(--text-primary)',
        secondary: 'var(--text-secondary)',
      },
      backgroundColor: {
        main: 'var(--bg-main)',
        card: 'var(--bg-card)',
        elevated: 'var(--bg-elevated)',
      },
      borderColor: {
        DEFAULT: 'var(--border)',
      }
    },
  },
  plugins: [],
}
