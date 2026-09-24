/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        wandor: {
          dark: "#1C201B",
          text: "#1a1a1a",
          muted: "#767676",
          prompt: "#D9720F",
          bg: "#ffffff",
          surface: "#EBEDE7",
          border: "#e5e7eb",
          card: "#FAFAF8",
        },
        brand: {
          50: "#FCF0E4",
          100: "#F7DDBE",
          500: "#D9720F",
          600: "#A8560A",
          700: "#7A3E07",
          900: "#4A2504",
        },
        steel: {
          50: "#EEF3F3",
          500: "#3C5A5E",
          600: "#2E4548",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        brand: ['"Bebas Neue"', "sans-serif"],
        arabic: ['"Scheherazade New"', "serif"],
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.04)",
        card: "0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.06)",
        dropdown: "0 4px 16px -2px rgba(0, 0, 0, 0.08), 0 2px 6px -2px rgba(0, 0, 0, 0.04)",
      },
    },
  },
  plugins: [],
};
