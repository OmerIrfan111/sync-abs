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
          surface: "#fbfbfa",
          border: "rgba(0, 0, 0, 0.07)",
          card: "rgba(255, 255, 255, 0.85)",
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
        "wandor-sm": "0 2px 8px rgba(0, 0, 0, 0.03)",
        "wandor-md": "0 8px 30px rgba(0, 0, 0, 0.04)",
        "wandor-lg": "0 18px 50px rgba(0, 0, 0, 0.06)",
        "wandor-float": "0 20px 60px rgba(10, 10, 10, 0.08)",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
        "4xl": "2rem",
      },
    },
  },
  plugins: [],
};
