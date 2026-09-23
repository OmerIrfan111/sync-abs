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
          dark: "#1B1B2F",
          text: "#1a1a1a",
          muted: "#767676",
          prompt: "#6C5DD3",
          bg: "#ffffff",
          surface: "#F6F6FB",
          border: "#e5e7eb",
          card: "#ffffff",
        },
        brand: {
          50: "#F3F1FD",
          100: "#E4DFFA",
          500: "#6C5DD3",
          600: "#5B4BD1",
          700: "#4A3BAE",
          900: "#2E2470",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
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
