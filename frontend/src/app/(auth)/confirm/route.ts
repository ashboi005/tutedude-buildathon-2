import { NextResponse, type NextRequest } from 'next/server';
import createClient from "@/lib/supabase/server";
import { type EmailOtpType } from "@supabase/supabase-js";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = "/create-profile";
  
  if (token_hash && type) {
    const supabase = await createClient();

    const { error } = await supabase.auth.verifyOtp({
      type,
      token_hash,
    });

    if (!error) {
      // CORRECT: Return a NextResponse redirect object
      const redirectUrl = new URL(next, request.url);
      return NextResponse.redirect(redirectUrl);
    } else {
      // CORRECT: Return a redirect for the error case
      const errorUrl = new URL("/error", request.url);
      errorUrl.searchParams.set("error", error.message);
      return NextResponse.redirect(errorUrl);
    }
  }

  // CORRECT: Return a redirect if params are missing
  const errorUrl = new URL("/error", request.url);
  errorUrl.searchParams.set("error", "No token hash or type provided.");
  return NextResponse.redirect(errorUrl);
}