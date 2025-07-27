// src/lib/apiClient.ts

import axios, { type AxiosInstance } from 'axios';
import createSupabaseClient from '@/lib/supabase/client';

// Create a new axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL, // Set this in your .env.local
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to automatically add the Supabase auth token.
// Supabase's getSession() method handles refreshing the token if it's expired.
apiClient.interceptors.request.use(async (config) => {
  const supabase = createSupabaseClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  
  return config;
});

// Optional: Add a response interceptor for generic error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // You can add generic error logging or handling here
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;