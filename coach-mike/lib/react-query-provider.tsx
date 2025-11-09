import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Create a shared query client for the application. In practice you might
// configure caching or logging here. We maintain a single instance to avoid
// recreating the client on every render.
const queryClient = new QueryClient();

export function ReactQueryClientProvider({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}