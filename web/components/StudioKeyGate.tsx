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
        if (!cancelled) {
          setStudioKey(storedKey);
          setGate("open");
        }
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

  if (gate === "checking") {
    return <p className="skeleton">Checking studio key…</p>;
  }

  return (
    <div className="grid flex-1 place-items-center px-5 py-20">
      <form
        className="flex w-full max-w-[380px] flex-col gap-4 border-2 border-[var(--color-text)] p-6"
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
        <div>
          <div className="label font-extrabold text-[var(--color-accent-700)]">Studio</div>
          <h1 className="mt-1 mb-0 text-[28px]">Enter your studio key</h1>
          <p className="mt-1 mb-0 text-[13px] text-[var(--color-neutral-800)]">
            Paste STUDIO_KEY from the server environment.
          </p>
        </div>
        <label className="field">
          <span className="field-label">Studio key</span>
          <input
            className="input h-11"
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            autoFocus
          />
        </label>
        {wrongKey ? (
          <p className="m-0 text-[13px] text-[var(--color-accent-700)]">{COPY.empty.wrongKey}</p>
        ) : null}
        <button className="btn btn-primary h-11 justify-start" type="submit">
          Enter
          <span className="ml-auto" aria-hidden>
            →
          </span>
        </button>
      </form>
    </div>
  );
}
