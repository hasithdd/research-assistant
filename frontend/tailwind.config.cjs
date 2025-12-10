/***********************************************************
 * Tailwind configuration for the Research Assistant UI.
 * Keeps content globs narrow to avoid scanning backend.
 ***********************************************************/
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#f7f7fb',
        ink: '#0f172a',
        accent: '#2563eb',
        muted: '#9ca3af'
      }
    }
  },
  darkMode: 'class',
  plugins: []
};
