import "./globals.css";

export const metadata = {
  title: "Tina Shen — Works",
  description:
    "Eighteen plates from six pieces of work in physics, applied mathematics and making things. Every card is painted from the maths it stands for.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
