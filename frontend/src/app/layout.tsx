import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const geist = Geist({ variable: "--font-geist", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Ledger Lens", template: "%s · Ledger Lens" },
  description: "Ask plain-language questions about bank statements from any bank, and see the exact rows behind every answer.",
};

// Applies a saved theme before first paint so there is no light flash.
const themeScript = `try{var t=localStorage.getItem("ledgerlens.theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geist.variable} ${geistMono.variable} antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-[100dvh] font-sans text-[14px]">
        {children}
        <Toaster position="bottom-right" toastOptions={{ className: "!font-sans !text-[13px]" }} />
      </body>
    </html>
  );
}
