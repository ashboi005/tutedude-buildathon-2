import { createBrowserClient } from "@supabase/ssr";
import env from "@/lib/env";

export default function createClient() {
  return createBrowserClient(env.supabaseUrl!, env.supabaseAnonKey!);
}
