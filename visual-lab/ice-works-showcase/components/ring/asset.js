// Anything served straight out of `public/`.
//
// Next rewrites the URLs it generates for `basePath`, but not strings written
// in our own code, and the published site lives under a path. So these are
// built rather than written — one place to be wrong instead of several.
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export const asset = (path) => `${BASE}${path}`;
