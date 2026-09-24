import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        safe: {
          green: "#10b981",
          yellow: "#f59e0b",
          orange: "#f97316",
          red: "#ef4444",
          dark: "#0f172a",
        },
      },
    },
  },
  plugins: [],
};
export default config;

