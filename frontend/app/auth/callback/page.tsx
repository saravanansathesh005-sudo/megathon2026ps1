"use client";

import { useEffect, useState } from "react";

import { setToken } from "@/lib/api";

/** Receives the token from the backend OAuth redirect and lands the user in the app. */
export default function AuthCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const token = hash.get("token");
    if (!token) { setError("Sign-in did not return a session."); return; }
    setToken(token);
    window.location.replace("/");
  }, []);

  return (
    <main className="grid min-h-screen place-items-center px-4 text-center">
      {error ? (
        <div>
          <p className="text-sm text-rose-300">{error}</p>
          <a href="/" className="mt-3 inline-block text-xs text-slate-400 underline">Try again</a>
        </div>
      ) : (
        <p className="text-sm text-slate-500">Signing you in…</p>
      )}
    </main>
  );
}
