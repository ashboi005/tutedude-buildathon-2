import createClient from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import React from "react";

export default async function ProtectedRoute() {
  const supabase = await createClient();

  const { data, error } = await supabase.auth.getClaims();
  if (error || !data?.claims) {
    redirect("/sign-in");
  }
  return <div>this is a protected route</div>;
}
