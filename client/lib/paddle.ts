"use client";

// Paddle.js v2, loaded on demand: opens Paddle's checkout overlay for a transaction the gateway created.

interface PaddleEvent {
  name?: string;
}

interface PaddleJs {
  Environment: { set: (env: string) => void };
  Initialize: (options: { token: string; eventCallback?: (event: PaddleEvent) => void }) => void;
  Checkout: { open: (options: { transactionId: string }) => void; close: () => void };
}

declare global {
  interface Window {
    Paddle?: PaddleJs;
  }
}

const SCRIPT_URL = "https://cdn.paddle.com/paddle/v2/paddle.js";
let ready: Promise<PaddleJs> | null = null;
let onCompleted: (() => void) | null = null; // the current checkout's handler (Initialize runs once per page)

function load(): Promise<PaddleJs> {
  ready ??= new Promise((resolve, reject) => {
    const token = process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;
    if (!token) return reject(new Error("Payments aren't configured on this site."));
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.onload = () => {
      const paddle = window.Paddle;
      if (!paddle) return reject(new Error("Couldn't load the payment form."));
      if ((process.env.NEXT_PUBLIC_PADDLE_ENV ?? "sandbox") === "sandbox") paddle.Environment.set("sandbox");
      paddle.Initialize({
        token,
        eventCallback: (event) => {
          if (event.name === "checkout.completed") onCompleted?.();
        },
      });
      resolve(paddle);
    };
    script.onerror = () => {
      ready = null;
      reject(new Error("Couldn't load the payment form. Check your connection and try again."));
    };
    document.head.appendChild(script);
  });
  return ready;
}

// Opens the overlay; `completed` runs once payment succeeds (credits then arrive via the webhook).
export async function openPaddleCheckout(transactionId: string, completed: () => void): Promise<void> {
  const paddle = await load();
  onCompleted = () => {
    onCompleted = null;
    completed();
  };
  paddle.Checkout.open({ transactionId });
}
