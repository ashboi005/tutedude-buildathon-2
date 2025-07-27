import { type EmailOtpType } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";
import  createClient  from '@/lib/supabase/server'; // <-- 1. Import the new server client

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  console.log('Callback route accessed:', request.url);
  if (token_hash && type) {
    const supabase = await createClient(); // <-- 2. Use the new client function

    const { error } = await supabase.auth.verifyOtp({
      type,
      token_hash,
    });

    if (!error) {
      if (type === 'signup') {
        return NextResponse.redirect(new URL('/create-profile', request.url));
      }
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }

  // Redirect to an error page if the link is invalid
  const url = new URL("/error", request.url);
  url.searchParams.set("message", "Invalid or expired verification link.");
  return NextResponse.redirect(url);
}