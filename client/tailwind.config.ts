import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#f5f5f7",
        surface: "#ffffff",
        ink: "#1d1d1f",
        "ink-secondary": "#6e6e73",
        divider: "#d2d2d7",
        primary: "#00695c",
        "primary-hover": "#004d40",
        error: "#ff3b30",
        link: "#007aff",
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", '"SF Pro Text"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        ambient: "0 8px 24px rgba(0, 0, 0, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
