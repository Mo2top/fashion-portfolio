# fashion-portfolio

My creative portfolio website, built with React and Vite. A minimal, responsive
starter with sections for selected work, an introduction, and contact information.

## Getting started

Use Node.js 24 LTS (see `.nvmrc`) and npm. Node.js 22.12 or newer is required.

```sh
npm ci
npm run dev
```

If your environment restricts writes to your home directory, use
`npm ci --cache /tmp/fashion-portfolio-npm-cache` instead.

The development server binds to all interfaces on port **5173** for cloud
development. The port is fixed in `vite.config.js`; startup fails if it is already
in use rather than silently switching ports.

```sh
npm run dev
```

## Production build

```sh
npm run build
npm run preview
```

The build is generated in `dist/`. Deploy that directory to a static hosting
service. `preview` is for checking the build locally, not a production server.
It uses port **4173**. Use **5173** for the live development app.

Cloud environment restarts stop running servers. Start `npm run dev` again from
the repository directory after a restart. A blank cloud preview can also mean
the preview is forwarding a different port; its target must match **5173**.

## Make it yours

- Edit `src/App.jsx` to replace Your Name, the sample projects, biography, and
  `hello@example.com` with your details.
- Adjust colors, typography, and layout in `src/styles.css`.
- Update the page title and description in `index.html`.
- Replace the decorative project placeholders with your own images when ready.

No backend services, credentials, or environment variables are needed.
