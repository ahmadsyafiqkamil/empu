"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { apiGet, getStudioKey, setStudioKey } from "@/lib/api";
import { COPY } from "@/lib/copy";
import { isStudioKeySubmittable, isStudioKeyUnauthorized } from "@/lib/studioKeyGate";

function subscribe(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  return () => window.removeEventListener("storage", onStoreChange);
}

type GateState = "checking" | "locked" | "open";

export function StudioKeyGate({ children }: { children: React.ReactNode }) {
  const [key, setKey] = useState("");
  const [wrongKey, setWrongKey] = useState(false);
  const [gate, setGate] = useState<GateState>("checking");
  const storedKey = useSyncExternalStore(subscribe, getStudioKey, () => "");

  useEffect(() => {
    let cancelled = false;

    async function checkStored() {
      if (!isStudioKeySubmittable(storedKey)) {
        if (!cancelled) setGate("locked");
        return;
      }
      if (!cancelled) setGate("checking");
      try {
        await apiGet<unknown>("/api/archives");
        if (!cancelled) setGate("open");
      } catch (error) {
        if (cancelled) return;
        setStudioKey("");
        setWrongKey(isStudioKeyUnauthorized(error));
        setGate("locked");
      }
    }

    void checkStored();
    return () => {
      cancelled = true;
    };
  }, [storedKey]);

  if (gate === "open") return children;
  if (gate === "checking") return null;

  return (
    <form
      className="mx-auto mt-24 max-w-sm space-y-3 p-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (!isStudioKeySubmittable(key)) return;
        setWrongKey(false);
        setStudioKey(key.trim());
        void (async () => {
          try {
            await apiGet<unknown>("/api/archives");
            setGate("open");
          } catch (error) {
            setStudioKey("");
            setWrongKey(isStudioKeyUnauthorized(error));
            setGate("locked");
          }
        })();
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
      {wrongKey ? (
        <p className="text-sm text-[var(--muted)]">{COPY.empty.wrongKey}</p>
      ) : null}
      <button className="bg-[var(--accent)] px-4 py-2 text-black" type="submit">
        Enter
      </button>
    </form>
  );
}
