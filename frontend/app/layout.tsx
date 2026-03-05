export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'Inter, sans-serif', margin: 0, background: '#0f172a', color: '#e2e8f0' }}>
        <main style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>{children}</main>
      </body>
    </html>
  );
}
