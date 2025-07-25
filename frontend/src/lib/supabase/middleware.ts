import { type NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

import env from "@/lib/env";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(env.supabaseUrl!, env.supabaseAnonKey!, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value }) => {
            request.cookies.set(name, value);
          });

          supabaseResponse = NextResponse.next({ request });

          cookiesToSet.forEach(({ name, value, options }) => {
            supabaseResponse.cookies.set(name, value, options);
          });
        } catch {}
      },
    },
  });

  // DO NOT ADD ANY CODE BTW `createServerClient` and `supabase.auth.getUser`
  // PLEASE

  await supabase.auth.getUser();

  return supabaseResponse;
}
