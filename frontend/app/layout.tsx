import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ToastProvider } from "@/components/ui/Toast";
import { EntitlementProvider } from "@/hooks/useEntitlement";
import { PaywallModal } from "@/components/billing/PaywallModal";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Roammate - Your Intelligent Itinerary Planner",
  description: "Adaptive itinerary planner with real-time concierge adaptation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <EntitlementProvider>
          <ToastProvider>{children}</ToastProvider>
          <PaywallModal />
        </EntitlementProvider>
      </body>
    </html>
  );
}
