import "./globals.css";

export const metadata = {
  title: "Tina Shen — A Personal Observatory",
  description:
    "Five worlds at the intersection of physics, applied mathematics and making things. Selected research and projects by Xinming (Tina) Shen.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
