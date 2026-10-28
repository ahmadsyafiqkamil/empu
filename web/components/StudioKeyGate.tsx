"use client";

import { useState, useSyncExternalStore } from "react";
import { getStudioKey, setStudioKey } from "@/lib/api";

function subscribe(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  return () => window.removeEventListener("storage", onStoreChange);
}

export function StudioKeyGate({ children }: { children: React.ReactNode }) {
  const [entered, setEntered] = useState(false);
  const [key, setKey] = useState("");
  const storedKey = useSyncExternalStore(subscribe, getStudioKey, () => "");

  if (entered || storedKey) return children;

  return (
    <form
      className="mx-auto mt-24 max-w-sm space-y-3 p-6"
      onSubmit={(e) => {
        e.preventDefault();
        setStudioKey(key);
        setEntered(true);
      }}
    >
      <h1 className="text-xl font-medium">Studio key</h1>
      <p className="text-sm text-[var(--muted)]">Paste STUDIO_KEY from the server environment.</p>
      <input
        className="w-full border border-[var(--line)] bg-transparent px-3 py-2"
        type="password"
        value={key}
        onChange={(e) => setKey(e.target.value)}
      />
      <button className="bg-[var(--accent)] px-4 py-2 text-black" type="submit">
        Enter
      </button>
    </form>
  );
}
