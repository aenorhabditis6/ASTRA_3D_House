/** @type {import('next').NextConfig} */

// Set by the Pages workflow at build time and empty everywhere else, so the
// app is at / in development and under /ASTRA_3D_House/works on the published
// site. Next rewrites its own URLs for this; anything of ours that reaches
// into `public/` has to prefix it itself — see components/ring/asset.js and
// the @font-face block in app/layout.js.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig = {
  // Nothing here needs a server: two routes, both static, and one WebGL
  // canvas. Exporting always rather than only in CI keeps what is published
  // the same build as what is developed against.
  output: "export",
  basePath,
  // A static host serves a directory from its index.html, so every route has
  // to be a directory rather than a bare .html file.
  trailingSlash: true,
  images: { unoptimized: true },
  turbopack: {
    root: import.meta.dirname,
  },
};

export default nextConfig;
