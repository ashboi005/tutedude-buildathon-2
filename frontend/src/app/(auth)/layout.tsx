import React from "react";

export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <main className="flex p-4 flex-col h-screen items-center justify-center">
      {children}
    </main>
  );
}
