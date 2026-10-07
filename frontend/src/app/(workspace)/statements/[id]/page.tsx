import type { Metadata } from "next";
import { StatementDetail } from "@/components/statements/StatementDetail";

export const metadata: Metadata = { title: "Statement" };

export default async function StatementPage(props: PageProps<"/statements/[id]">) {
  const { id } = await props.params;
  return <StatementDetail id={id} />;
}
