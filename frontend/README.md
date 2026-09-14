# DailyRandomz frontend

See [the project README](../readme.MD) for the complete setup and PWA testing instructions.

```bash
npm ci
npm run dev
npm run lint
npm run build
```

## Themes

Use the header's Theme selector to choose Light, Dark, or System. The choice is stored on this device, works without signing in, and syncs between tabs. System follows the operating system's appearance setting, including changes while the app is open.

Color palettes live in `src/index.css` as CSS custom properties. Components use semantic variables such as `--background`, `--text`, and `--accent` in `src/App.css`. Light uses neon green on white; dark uses purple on near-black. Use `--accent-text` for readable colored text and `--accent` for filled buttons and decoration.

`index.html` applies the theme before the first paint; `src/ThemePicker.jsx` handles changes and storage. The page's theme-color metadata follows the selected theme; the install manifest uses a static white launch background.
