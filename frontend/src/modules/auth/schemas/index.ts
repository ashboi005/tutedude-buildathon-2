import { z } from "zod";

export const vendorSignUpSchema = z.object({
  username: z.string().min(1, { message: "Username is required" }),
  email: z.email({ message: "Invalid email address" }),
  phoneNo: z.string().min(1, { message: "Phone number is required" }),
  password: z
    .string()
    .min(6, { message: "Password must be at least 6 characters" }),
});

export const supplierSignUpSchema = z.object({
  username: z.string().min(1, { message: "Username is required" }),
  email: z.email({ message: "Invalid email address" }),
  phoneNo: z.string().min(1, { message: "Phone number is required" }),
  gstNo: z.string().min(1, { message: "GST number is required" }),
  companyName: z.string().min(1, { message: "Company name is required" }),
  address: z.string().min(1, { message: "Address is required" }),
  password: z
    .string()
    .min(6, { message: "Password must be at least 6 characters" }),
})

export const signInSchema = z.object({
  email: z.email({ message: "Invalid email address" }),
  password: z
    .string()
    .min(6, { message: "Password must be at least 6 characters" }),
});
