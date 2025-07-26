import apiClient from '@/lib/apiClient';
import type { CreateProfilePayload, Profile } from '@/types/auth.types';

// Define the response type for the image upload endpoint
interface UploadProfileImageResponse {
  avatar_url: string;
  message: string;
}

export const authApi = {
  /**
   * Creates a new user profile with the provided data.
   */
  createProfile: async (data: CreateProfilePayload): Promise<Profile> => {
    const response = await apiClient.post('/auth/create-profile', data);
    return response.data;
  },

  /**
   * Uploads a profile image for the currently authenticated user.
   * @param imageFile The image file to upload (e.g., from an <input type="file">).
   */
  uploadProfileImage: async (imageFile: File): Promise<UploadProfileImageResponse> => {
    const formData = new FormData();
    formData.append('file', imageFile); // The key 'file' must match your API's expected key

    const response = await apiClient.post('/users/me/profile-image', formData, {
      headers: {
        // Axios and modern browsers will automatically set the 'Content-Type'
        // to 'multipart/form-data' with the correct boundary when you pass a FormData object.
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },
};