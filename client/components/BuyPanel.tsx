"use client";

import { useEffect, useState } from "react";
import { Sheet } from "@/components/Sheet";
import { openPaddleCheckout } from "@/lib/paddle";
import { gatewayFetch } from "@/lib/supabase";
import { PRIMARY } from "@/lib/ui";

interface Product {
  id: string;
  label: string;
  price: string;
}

// Pick a product, then pay in the provider's checkout (Paddle overlay, or Stripe's hosted page).
// Credits arrive via the provider's webhook; /new?paid=1 waits for them.
export function BuyPanel({ open, onClose, reason }: { open: boolean; onClose: () => void; reason?: string }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [choice, setChoice] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || products.length) return;
    gatewayFetch<Product[]>("/billing/products").then(
      (list) => {
        setProducts(list);
        setChoice(list[0]?.id ?? "");
      },
      () => setError("Can't load prices right now."),
    );
  }, [open, products.length]);

  const pay = async () => {
    setBusy(true);
    setError(null);
    try {
      const checkout = await gatewayFetch<{ provider: string; url?: string; transaction_id?: string }>("/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product: choice }),
      });
      if (checkout.transaction_id) {
        await openPaddleCheckout(checkout.transaction_id, () => window.location.assign("/new?paid=1"));
        setBusy(false);
        onClose(); // Paddle's overlay is open now; our sheet would sit on top of it
      } else if (checkout.url) {
        window.location.assign(checkout.url);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title="Get more mock interviews">
      <div className="space-y-4 px-5 py-4">
        {reason && <p className="text-ink">{reason}</p>}
        <fieldset className="space-y-2">
          <legend className="sr-only">Choose a plan</legend>
          {products.map((p) => (
            <label
              key={p.id}
              className="flex cursor-pointer items-center justify-between gap-4 rounded-[8px] border border-divider p-4 has-[:checked]:border-primary has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-primary"
            >
              <span className="flex items-center gap-3">
                <input type="radio" name="product" checked={choice === p.id} onChange={() => setChoice(p.id)} />
                <span className="font-semibold text-ink">{p.label}</span>
              </span>
              <span className="text-lg font-bold text-ink tabular-nums">{p.price}</span>
            </label>
          ))}
        </fieldset>
        {error && (
          <p role="alert" className="text-sm text-error">
            {error}
          </p>
        )}
        <button onClick={() => void pay()} disabled={busy || !choice} className={`${PRIMARY} w-full`}>
          {busy ? "Opening secure checkout…" : "Continue to payment"}
        </button>
        <p className="text-xs text-ink-secondary">Payment is handled securely by our payment provider. We never see your card details.</p>
      </div>
    </Sheet>
  );
}
