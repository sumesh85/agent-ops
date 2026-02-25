import { redirect } from "next/navigation";

// Root redirects to the Overview (Stability Overview) as the demo landing page.
export default function RootPage() {
  redirect("/overview");
}
