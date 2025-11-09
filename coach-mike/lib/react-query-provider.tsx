"use client";

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useState } from 'react';

// Create a shared query client for the application. In practice you might
// configure caching or logging here. We maintain a single instance to avoid
// recreating the client on every render.
export function ReactQueryClientProvider({ children }: { children: React.ReactNode }) {
  // Create QueryClient in state to ensure it's only created once per component instance
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
      },
    },
  }));

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}