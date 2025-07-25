import React from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VendorSignUpForm } from "@/modules/auth/ui/components/vendor-sign-up-form";
import { SupplierSignUpForm } from "../components/supplier-sign-up-form";
import { SignInForm } from "../sign-in-form";

export default function SignInView() {
  return (
    <div className="flex flex-col gap-2 w-[90%] md:w-1/3">
      <div className="text-center gap-2 flex flex-col">
        <span className="font-semibold tracking-tight md:text-4xl text-3xl">
          Sign In
        </span>
        <p className="text-muted-foreground text-lg">
          Welcome back to our community.
        </p>
      </div>
      <Card>
        <CardHeader className="gap-[2px]">
          <CardTitle className="text-lg">Access Account</CardTitle>
          <CardDescription>
            Enter your credentials to access your account.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SignInForm />
        </CardContent>
      </Card>
    </div>
  );
}
