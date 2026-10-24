/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ns: {
          primary: 'rgb(var(--ns-primary-rgb) / <alpha-value>)',
          'primary-hover': 'rgb(var(--ns-primary-hover-rgb) / <alpha-value>)',
          'primary-light': 'rgb(var(--ns-primary-light-rgb) / <alpha-value>)',
          'primary-dark': 'rgb(var(--ns-primary-dark-rgb) / <alpha-value>)',
          aqua: 'rgb(var(--ns-aqua-rgb) / <alpha-value>)',
          black: 'rgb(var(--ns-black-rgb) / <alpha-value>)',
          background: 'rgb(var(--ns-background-rgb) / <alpha-value>)',
          surface: 'rgb(var(--ns-surface-rgb) / <alpha-value>)',
          'surface-secondary': 'rgb(var(--ns-surface-secondary-rgb) / <alpha-value>)',
          'text-primary': 'rgb(var(--ns-text-primary-rgb) / <alpha-value>)',
          'text-secondary': 'rgb(var(--ns-text-secondary-rgb) / <alpha-value>)',
          'text-muted': 'rgb(var(--ns-text-muted-rgb) / <alpha-value>)',
          border: 'rgb(var(--ns-border-rgb) / <alpha-value>)',
          divider: 'rgb(var(--ns-divider-rgb) / <alpha-value>)',
          success: 'rgb(var(--ns-success-rgb) / <alpha-value>)',
          warning: 'rgb(var(--ns-warning-rgb) / <alpha-value>)',
          danger: 'rgb(var(--ns-danger-rgb) / <alpha-value>)',
          info: 'rgb(var(--ns-info-rgb) / <alpha-value>)'
        },
        brand: {
          50: 'rgb(var(--ns-primary-light-rgb) / <alpha-value>)',
          100: 'rgb(var(--ns-primary-100-rgb) / <alpha-value>)',
          200: 'rgb(var(--ns-primary-200-rgb) / <alpha-value>)',
          300: 'rgb(var(--ns-primary-300-rgb) / <alpha-value>)',
          400: 'rgb(var(--ns-aqua-rgb) / <alpha-value>)',
          500: 'rgb(var(--ns-primary-rgb) / <alpha-value>)',
          600: 'rgb(var(--ns-primary-hover-rgb) / <alpha-value>)',
          700: 'rgb(var(--ns-primary-dark-rgb) / <alpha-value>)',
          800: 'rgb(var(--ns-primary-800-rgb) / <alpha-value>)',
          900: 'rgb(var(--ns-primary-900-rgb) / <alpha-value>)',
          950: 'rgb(var(--ns-primary-950-rgb) / <alpha-value>)'
        },
        mint: {
          50: 'rgb(var(--ns-surface-rgb) / <alpha-value>)',
          100: 'rgb(var(--ns-background-rgb) / <alpha-value>)',
          200: 'rgb(var(--ns-surface-secondary-rgb) / <alpha-value>)',
          300: 'rgb(var(--ns-border-rgb) / <alpha-value>)',
          400: 'rgb(var(--ns-text-muted-rgb) / <alpha-value>)'
        },
        ink: {
          DEFAULT: 'rgb(var(--ns-text-primary-rgb) / <alpha-value>)',
          soft: 'rgb(var(--ns-text-secondary-rgb) / <alpha-value>)',
          faint: 'rgb(var(--ns-text-muted-rgb) / <alpha-value>)'
        }
      },
      borderRadius: {
        neo: '8px',
        'neo-lg': '8px',
        'neo-sm': '6px'
      },
      boxShadow: {
        neo: '0 1px 3px rgb(7 27 36 / 6%), 0 1px 2px rgb(7 27 36 / 4%)',
        'neo-sm': '0 1px 2px rgb(7 27 36 / 5%)',
        'neo-lg': '0 4px 12px rgb(7 27 36 / 8%)',
        'neo-inset': 'inset 0 1px 2px rgb(7 27 36 / 5%)',
        'neo-btn': '0 1px 2px rgb(7 27 36 / 8%)'
      },
      fontFamily: {
        sans: ['"Inter Variable"', 'Inter', 'system-ui', 'sans-serif']
      },
      keyframes: {
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgb(27 171 206 / 35%)' },
          '70%': { boxShadow: '0 0 0 12px rgb(27 171 206 / 0%)' },
          '100%': { boxShadow: '0 0 0 0 rgb(27 171 206 / 0%)' }
        }
      },
      animation: {
        'pulse-ring': 'pulse-ring 2s infinite'
      }
    }
  },
  plugins: []
};
