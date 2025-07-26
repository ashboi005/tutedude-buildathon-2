"use client";

import { useEffect, useState, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Loader2, Upload } from "lucide-react";

// Your custom components
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// Your API and Supabase client
import { authApi } from "@/lib/api/auth";
import createClient from "@/lib/supabase/client";

// --- Zod Schema for Validation ---
// Includes validation for all fields, including the uploaded file.
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];

const profileSchema = z.object({
  username: z.string()
    .min(3, "Username must be at least 3 characters")
    .max(50, "Username must be less than 50 characters")
    .regex(/^[a-zA-Z0-9_]+$/, "Username can only contain letters, numbers, and underscores"),
  fullName: z.string()
    .min(1, "Full name is required")
    .max(100, "Full name must be less than 100 characters"),
  bio: z.string()
    .max(500, "Bio must be less than 500 characters")
    .optional(),
  profilePic: z.any() // Start with z.any() to prevent SSR errors
    .refine(
      (files) => {
        // On the server, 'files' will be undefined, so we bypass validation.
        // On the client, we check if it's a FileList.
        if (typeof window === 'undefined') return true;
        return files instanceof FileList;
      },
      { message: "Invalid file input." }
    )
    .refine((files) => !files || files.length === 0 || files[0].size <= MAX_FILE_SIZE, `Max file size is 5MB.`)
    .refine(
      (files) => !files || files.length === 0 || ACCEPTED_IMAGE_TYPES.includes(files[0].type),
      "Only .jpg, .png, .gif, and .webp formats are supported."
    ).optional(),
  role: z.enum(["vendor", "supplier"]),
  date_of_birth: z.string().optional().refine((date) => {
    if (!date) return true; // Optional field is valid if empty
    const age = new Date().getFullYear() - new Date(date).getFullYear();
    return age >= 13 && age <= 120;
  }, "You must be between 13 and 120 years old."),
  language: z.string(),
  timezone: z.string(),
});

type ProfileFormData = z.infer<typeof profileSchema>;

export default function CreateProfilePage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isValid },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    mode: "onChange",
    defaultValues: {
      language: "en",
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    },
  });

  // --- Authentication & Pre-filling ---
  useEffect(() => {
    const checkAuth = async () => {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        toast.error("Authentication session not found. Please log in again.");
        router.push("/sign-in");
        return;
      }

      const { user_metadata } = session.user;
      setValue("username", user_metadata.name || "", { shouldValidate: true });
      setValue("fullName", user_metadata.full_name || user_metadata.name || "", { shouldValidate: true });
      if (user_metadata.role && ["vendor", "supplier"].includes(user_metadata.role)) {
        setValue("role", user_metadata.role as "vendor" | "supplier", { shouldValidate: true });
      }

      setIsCheckingAuth(false);
    };

    checkAuth();
  }, [router, setValue]);

  // --- Form Submission Handler ---
  const onSubmit = async (data: ProfileFormData) => {
    setIsLoading(true);
    const { profilePic, ...profileData } = data;
    const imageFile = profilePic?.[0];

    try {
      const nameParts = profileData.fullName.split(' ');
      const firstName = nameParts[0];
      const lastName = nameParts.slice(1).join(' ') || firstName;

      toast.info("Creating profile...");
      await authApi.createProfile({
        username: profileData.username,
        first_name: firstName,
        last_name: lastName,
        bio: profileData.bio || undefined,
        role: profileData.role,
        language: profileData.language,
        timezone: profileData.timezone,
        date_of_birth: profileData.date_of_birth ? `${profileData.date_of_birth}T00:00:00Z` : undefined,
      });

      if (imageFile) {
        toast.info("Uploading profile picture...");
        await authApi.uploadProfileImage(imageFile);
      }

      toast.success("Profile created successfully!");
      router.push("/dashboard");

    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : "An unexpected error occurred.";
      toast.error(`Operation failed: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Avatar File Change Handler for Preview ---
  const { ref: fileInputRef, onChange: onFileChange, ...fileInputRest } = register("profilePic");

  const handleAvatarChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAvatarPreview(URL.createObjectURL(file));
    } else {
      setAvatarPreview(null);
    }
    onFileChange(e); // Pass event to react-hook-form's handler
  };

  // --- Render Logic ---
  if (isCheckingAuth) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
      </div>
    );
  }

  // Custom class for select to match input style
  const selectClassName = `w-full h-10 px-3 py-2 text-sm bg-transparent border rounded-md ${errors.role ? 'border-red-500' : 'border-input'}`;

  return (
    <div className="min-h-screen flex items-center justify-center bg-white py-12">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="bg-gray-50 border p-6 rounded-xl shadow-md w-full max-w-lg space-y-6"
      >
        <h2 className="text-2xl font-bold text-center text-gray-800">Complete Your Profile</h2>

        {/* Profile Pic Upload */}
        <div className="flex flex-col items-center gap-4">
          <div className="relative h-24 w-24">
            {avatarPreview ? (
              <Image
                src={avatarPreview}
                alt="Profile Preview"
                fill
                className="rounded-full object-cover border-2 border-red-500"
              />
            ) : (
              <div className="h-full w-full rounded-full bg-gray-200 flex items-center justify-center text-gray-500 text-xs border">
                No image
              </div>
            )}
          </div>
          <Button type="button" variant="outline" asChild>
            <label htmlFor="profilePic-upload" className="cursor-pointer flex items-center">
              <Upload className="h-4 w-4 mr-2" />
              Upload Profile Picture
            </label>
          </Button>
          <input
            id="profilePic-upload"
            type="file"
            className="hidden"
            accept="image/png, image/jpeg, image/webp, image/gif"
            {...fileInputRest}
            ref={fileInputRef}
            onChange={handleAvatarChange}
          />
        
        </div>

        {/* Form Fields */}
        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input id="username" placeholder="e.g. funkyfresh" {...register("username")} />
          {errors.username && <p className="text-red-500 text-sm mt-1">{errors.username.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="fullName">Full Name</Label>
          <Input id="fullName" placeholder="e.g. Funky Fresh" {...register("fullName")} />
          {errors.fullName && <p className="text-red-500 text-sm mt-1">{errors.fullName.message}</p>}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
                <Label htmlFor="role">Role *</Label>
                <select id="role" {...register("role")} className={selectClassName}>
                    <option value="">Select a role...</option>
                    <option value="vendor">Vendor</option>
                    <option value="supplier">Supplier</option>
                </select>
                {errors.role && <p className="text-red-500 text-sm mt-1">{errors.role.message}</p>}
            </div>
            <div className="space-y-2">
                <Label htmlFor="date_of_birth">Date of Birth</Label>
                <Input type="date" id="date_of_birth" {...register("date_of_birth")} />
                {errors.date_of_birth && <p className="text-red-500 text-sm mt-1">{errors.date_of_birth.message}</p>}
            </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="bio">Bio</Label>
          <Textarea id="bio" placeholder="Tell us something cool about you" {...register("bio")} />
          {errors.bio && <p className="text-red-500 text-sm mt-1">{errors.bio.message}</p>}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
                <Label htmlFor="language">Language *</Label>
                <select id="language" {...register("language")} className={selectClassName}>
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="hi">Hindi</option>
                </select>
                {errors.language && <p className="text-red-500 text-sm mt-1">{errors.language.message}</p>}
            </div>
            <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Input id="timezone" {...register("timezone")} readOnly />
                {errors.timezone && <p className="text-red-500 text-sm mt-1">{errors.timezone.message}</p>}
            </div>
        </div>

        <Button type="submit" className="w-full bg-red-500 text-white hover:bg-red-600" disabled={isLoading || !isValid}>
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save Details"}
        </Button>
      </form>
    </div>
  );
}
