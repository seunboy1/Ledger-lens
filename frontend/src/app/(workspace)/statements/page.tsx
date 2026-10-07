import type { Metadata } from "next";
import { StatementsView } from "@/components/statements/StatementsView";

export const metadata: Metadata = { title: "Statements" };

export default function StatementsPage() {
  return <StatementsView />;
}
