/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Montserrat", "Calibri", "system-ui", "sans-serif"],
      },
      colors: {
        credo: {
          dark: "#575756",
          light: "#DADADA",
        },
        schule: {
          gym: "#FBC900",
          ges: "#6BAA24",
          gsm: "#E2001A",
          // Dunkleres Blau fuer ausreichenden Kontrast auf weiss (WCAG AA).
          gsh: "#0077A8",
          gss: "#AD1C28",
        },
      },
    },
  },
  plugins: [],
};
