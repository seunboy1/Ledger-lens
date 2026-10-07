import type { Metadata } from "next";
import { SignInPanel } from "@/components/SignInPanel";

export const metadata: Metadata = { title: "Sign in" };

export default function SignInPage() {
  return <SignInPanel />;
}
