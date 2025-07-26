// src/features/auth/types/index.ts

/**
 * Defines the possible roles for a user in the application.
 */
export type Role = 'vendor' | 'supplier' | 'user';

/**
 * Represents the data payload required to create a new user profile
 * via the POST /auth/create-profile endpoint. This matches the API schema.
 */
export interface CreateProfilePayload {
  username: string;
  role: Role;
  first_name?: string;
  last_name?: string;
  display_name?: string;
  bio?: string;
  avatar_url?: string;
  date_of_birth?: string; // Should be in ISO 8601 format, e.g., "2025-07-26T18:27:30.015Z"
  timezone?: string;
  language?: string;
  preferences?: Record<string, any>;
}

/**
 * Represents the full user profile object as it is returned by the API.
 * This matches the API's successful response schema.
 */
export interface Profile {
  id: string;
  user_id: string;
  email: string;
  username: string;
  role: Role;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  date_of_birth: string | null;
  timezone: string | null;
  language: string | null;
  preferences: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}