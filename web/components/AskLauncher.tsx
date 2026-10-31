"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import { MessageSquare } from "lucide-react";
import { AskPanel } from "./AskPanel";
import { AskSheet } from "./AskSheet";
import { COPY } from "@/lib/copy";
import { archiveSlugFromPathname, pickArchiveSlug, shouldShowLauncher } from "@/lib/askUi";
import {
  closeAsk,
  getAskServerSnapshot,
  getAskSnapshot,
  openAsk,
  subscribeAsk,
  toggleAsk,
} from "@/lib/askStore";
import type { Archive } from "@/lib/types";

/**
 * One floating entry point for every public screen, mounted in the root layout.
 *
 * The page behind the sheet keeps its scroll position and its reading context; the
 * panel is mounted only while open, so opening it always starts a fresh turn.
 */
export function AskLauncher() {
  const pathname = usePathname() ?? "/";
  const visible = shouldShowLauncher(pathname);
  const pathSlug = archiveSlugFromPathname(pathname);
  const [fallbackSlug, setFallbackSlug] = useState<string | null>(null);
  const [lookedUp, setLookedUp] = useState(false);
  const state = useSyncExternalStore(subscribeAsk, getAskSnapshot, getAskServerSnapshot);

  useEffect(() => {
    if (!visible || pathSlug) return;
    let cancelled = false;
    fetch("/api/public/archives", { cache: "no-store" })
      .then((response) => (response.ok ? (response.json() as Promise<Archive[]>) : []))
      .then((archives) => {
        if (!cancelled) setFallbackSlug(pickArchiveSlug(archives));
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLookedUp(true);
      });
    return () => {
      cancelled = true;
    };
  }, [visible, pathSlug]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        toggleAsk();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (!visible) return null;

  const slug = pathSlug ?? fallbackSlug;
  const ready = Boolean(pathSlug) || lookedUp;
  const token = state.request?.token ?? 0;

  return (
    <>
      <button
        type="button"
        className="btn btn-primary ask-launcher"
        aria-haspopup="dialog"
        aria-expanded={state.open}
        aria-controls="empu-ask-sheet"
        onClick={() => openAsk()}
      >
        <MessageSquare className="size-4" aria-hidden />
        {COPY.ask.launcher}
        <span className="ml-1 text-[11px] opacity-70" aria-hidden>
          {COPY.ask.shortcut}
        </span>
      </button>

      <AskSheet open={state.open} onClose={closeAsk} title={COPY.ask.title}>
        {state.open ? (
          slug ? (
            <AskPanel
              key={token}
              endpoint={`/api/public/archives/${slug}/ask`}
              slug={slug}
              initialQuestion={state.request?.question ?? ""}
              autoSend={state.request?.autoSend ?? false}
            />
          ) : (
            <div className="empty">
              <span>{ready ? COPY.ask.unavailable : COPY.ask.thinking}</span>
            </div>
          )
        ) : null}
      </AskSheet>
    </>
  );
}
