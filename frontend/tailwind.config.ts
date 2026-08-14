import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f7f4",
          100: "#dceee6",
          600: "#1f6b4f",
          700: "#18553f",
          900: "#0f2f24",
        },
      },
    },
  },
  plugins: [],
};

export default config;
