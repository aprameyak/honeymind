/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1220",
        panel: "#121a2b",
        line: "#243049",
        accent: "#3ecf8e",
        warn: "#f0b429",
        danger: "#ef5f5f",
        mute: "#8b9bb4",
      },
      fontFamily: {
        display: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        grid: "radial-gradient(circle at 1px 1px, rgba(62,207,142,0.12) 1px, transparent 0)",
      },
    },
  },
  plugins: [],
};
