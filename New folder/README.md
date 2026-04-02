# VQMS Flow Explorer — Local Development Setup

## Prerequisites

- [Node.js](https://nodejs.org/) (v18 or higher)
- npm (comes with Node.js)

## What Was Set Up

Vite is a fast build tool that serves your React JSX file with **hot module replacement (HMR)** — the browser updates instantly every time you save the file.

### Files Created

| File | Purpose |
|------|---------|
| `package.json` | Project config, dependencies, and scripts |
| `vite.config.js` | Vite configuration with React plugin |
| `index.html` | Entry HTML file (Vite uses this as the app shell) |
| `main.jsx` | React entry point — imports `App` from your JSX file and mounts it to the DOM |

### How It Connects

```
index.html
  └── loads main.jsx (via <script type="module">)
        └── imports App from VQMS_Flow_Explorer.jsx
              └── mounts to <div id="root">
```

---

## Step-by-Step Setup (From Scratch)

If you ever need to recreate this setup in a new folder:

### 1. Create `package.json`

```bash
npm init -y
```

Then edit it to add dependencies and scripts, or just create it with this content:

```json
{
  "name": "vqms-flow-explorer",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0"
  }
}
```

### 2. Create `vite.config.js`

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
```

This tells Vite to use the React plugin, which handles JSX transformation and fast refresh.

### 3. Create `index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>VQMS Flow Explorer</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/main.jsx"></script>
  </body>
</html>
```

Vite uses `index.html` as the entry point (not a JS file like Webpack). The `<script type="module">` tag loads your React app.

### 4. Create `main.jsx`

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './VQMS_Flow_Explorer'

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
```

This is the bridge between `index.html` and your `VQMS_Flow_Explorer.jsx` file.

### 5. Install Dependencies

```bash
npm install
```

This reads `package.json` and installs:
- `react` and `react-dom` — React library
- `vite` — dev server and build tool
- `@vitejs/plugin-react` — JSX and fast refresh support

### 6. Start the Dev Server

```bash
npm run dev
```

Output will look like:

```
VITE v6.x.x  ready in 400 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

Open **http://localhost:5173** in your browser.

---

## Daily Usage

```bash
# Start dev server (hot reload on save)
npm run dev

# Build for production (outputs to dist/)
npm run build

# Preview production build locally
npm run preview
```

## How Hot Reload Works

1. You edit `VQMS_Flow_Explorer.jsx` and save
2. Vite detects the file change
3. Only the changed module is re-sent to the browser
4. React state is preserved where possible (Fast Refresh)
5. The browser updates without a full page reload

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.
