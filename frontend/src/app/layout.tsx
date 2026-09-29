import type { Metadata } from 'next';
import React from 'react';
import '../styles/globals.css';
import { AuthProvider } from '../contexts/AuthContext';
import { LanguageProvider } from '../contexts/LanguageContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export const metadata: Metadata = {
  title: 'JanSeva AI - जनसेवा AI | मध्य प्रदेश शासन नागरिक निवारण पोर्टल',
  description:
    'JanSeva AI: मध्य प्रदेश शासन का आधिकारिक लोक शिकायत निवारण पोर्टल। SLA-आधारित समयबद्ध, पारदर्शी एवं जवाबदेह समाधान।',
  icons: {
    icon: '/logo.png',
    shortcut: '/logo.png',
    apple: '/logo.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/logo.png" type="image/png" />
      </head>
      <body>
        <AuthProvider>
          <LanguageProvider>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                minHeight: '100vh',
              }}
            >
              <Navbar />
              <main style={{ flex: 1 }}>{children}</main>
              <Footer />
            </div>
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
