import type { Metadata } from 'next';
import './globals.css';
import { SessionProvider } from 'next-auth/react';
import { ReactQueryClientProvider } from '../lib/react-query-provider';

export const metadata: Metadata = {
  title: 'Coach Mike',
  description: 'Votre entraîneur personnel alimenté par RAG',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="bg-gray-50 text-gray-900">
        <SessionProvider>
          <ReactQueryClientProvider>{children}</ReactQueryClientProvider>
        </SessionProvider>
      </body>
    </html>
  );
}