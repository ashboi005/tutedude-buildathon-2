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

export default function SignUpView() {
  return (
    <div className="flex flex-col gap-2 w-[90%] md:w-1/3">
      <div className="text-center gap-2 flex flex-col">
        <span className="font-semibold tracking-tight md:text-4xl text-3xl">
          Sign Up
        </span>
        <p className="text-muted-foreground text-lg">
          Join our community today.
        </p>
      </div>
      <Card>
        <CardHeader className="gap-[2px]">
          <CardTitle className="text-lg">Create Account</CardTitle>
          <CardDescription>
            Choose your account type and fill in your details
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="vendor" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="vendor">Vendor</TabsTrigger>
              <TabsTrigger value="supplier">Supplier</TabsTrigger>
            </TabsList>
            <TabsContent value="vendor">
              <VendorSignUpForm />
            </TabsContent>
            <TabsContent value="supplier">
              <SupplierSignUpForm />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
