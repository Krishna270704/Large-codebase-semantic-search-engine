/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      colors: {
        brand: {
          50: "#f0f6fc",
          100: "#c9d1d9",
          200: "#b1bac4",
          300: "#8b949e",
          400: "#58a6ff",
          500: "#2f81f7",
          600: "#1f6feb",
          700: "#1158c7",
          800: "#0d419d",
          900: "#0c2d6b",
          950: "#051d4d",
        },
        surface: {
          50: "#f0f6fc",
          100: "#c9d1d9",
          200: "#b1bac4",
          700: "#30363d",
          800: "#161b22",
          900: "#0d1117",
          950: "#010409",
        },
      },
      borderWidth: {
        3: "3px",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.35s ease-out",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "scale-in": "scaleIn 0.2s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
    },
  },
  plugins: [],
};
