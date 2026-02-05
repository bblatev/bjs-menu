"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Redirect page - redirects to /purchase-orders/management
 * The basic purchase orders page has been consolidated into the management page.
 */
export default function PurchaseOrdersRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/purchase-orders/management");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Redirecting to Purchase Order Management...</p>
      </div>
    </div>
  );
}
