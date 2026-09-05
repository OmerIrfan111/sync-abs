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
          dark: "#0a0a0a",
          text: "#1a1a1a",
          muted: "#767676",
          prompt: "#905831",
          bg: "#ffffff",
          surface: "#fafafa",
          border: "#e5e7eb",
          card: "#ffffff",
        },
        brand: {
          50: "#fdf8f4",
          100: "#faede3",
          500: "#905831",
          600: "#7b4724",
          700: "#64381b",
          900: "#3d1e0a",
        },
      },
      fontFamily: {
        sans: ["Geist", "system-ui", "sans-serif"],
        brand: ['"Special Elite"', "cursive"],
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
