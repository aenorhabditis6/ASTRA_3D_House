import "./globals.css";

export const metadata = {
  title: "Tina Shen — Works",
  description:
    "Six pieces of work in physics, applied mathematics and making things, three plates each. Every card is painted from the maths it stands for.",
};

// The three families are looked up BY NAME: the strings in ring/params.js
// (nameFont, idxFont, textFont) have to match a family declared here, and the
// textFont dropdown in ring/gui.js lists them a third time. A name with no
// matching block falls back to system sans silently, which looks like a
// rendering bug rather than a missing file.
//
// Declared here rather than in globals.css because a url() inside a stylesheet
// is not rewritten for `basePath`, and the published site lives under one.
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const face = (family, file, format, weight) =>
  `@font-face{font-family:"${family}";src:url("${BASE}/${file}") format("${format}");font-weight:${weight};font-style:normal;font-display:swap}`;

const FONTS = [
  // Project names and disciplines. Two real cuts, so nameWeight 400 and 500
  // both resolve to a drawn weight rather than a synthesised one.
  face("Satoshi", "Satoshi-Regular.otf", "opentype", 400),
  face("Satoshi", "Satoshi-Medium.otf", "opentype", 500),
  // Numbers, years and the load counter.
  face("Geist", "Geist-Regular.ttf", "truetype", 400),
].join("");

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-full flex flex-col">
        <style dangerouslySetInnerHTML={{ __html: FONTS }} />
        {children}
      </body>
    </html>
  );
}
