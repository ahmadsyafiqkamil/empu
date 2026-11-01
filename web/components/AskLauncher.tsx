"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import { MessageSquare } from "lucide-react";
import { AskPanel } from "./AskPanel";
import { AskSheet } from "./AskSheet";
import { COPY } from "@/lib/copy";
import { askSuggestionsAcross, type ArchiveTerms } from "@/lib/ask";
import { isTypingTarget, shouldCloseOnHide, shouldShowLauncher } from "@/lib/askUi";
import {
  closeAsk,
  getAskServerSnapshot,
  getAskSnapshot,
  openAsk,
  subscribeAsk,
  toggleAsk,
} from "@/lib/askStore";
import type { Archive, EntryListItem } from "@/lib/types";

/**
 * One floating entry point for every public screen, mounted in the root layout.
 *
 * Ask answers from every archive, so the sheet has one endpoint and no archive to
 * pick. The page behind the sheet keeps its scroll position; the panel is mounted
 * only while open, so opening it always starts a fresh turn.
 */
export function AskLauncher() {
  const pathname = usePathname() ?? "/";
  const visible = shouldShowLauncher(pathname);
  const [groups, setGroups] = useState<ArchiveTerms[] | null>(null);
  const state = useSyncExternalStore(subscribeAsk, getAskSnapshot, getAskServerSnapshot);

  useEffect(() => {
    if (!visible || !state.open || groups !== null) return;
    let cancelled = false;
    fetch("/api/public/archives", { cache: "no-store" })
      .then((response) => (response.ok ? (response.json() as Promise<Archive[]>) : []))
      .then(async (archives) => {
        const built = await Promise.all(
          archives.map(async (archive) => ({
            title: archive.title,
            terms: await fetch(`/api/public/archives/${archive.slug}/entries`, {
              cache: "no-store",
            })
              .then((response) =>
                response.ok ? (response.json() as Promise<EntryListItem[]>) : [],
              )
              .then((rows) => rows.map((row) => row.term))
              .catch(() => [] as string[]),
          })),
        );
        if (!cancelled) setGroups(built);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [visible, state.open, groups]);

  useEffect(() => {
    if (shouldCloseOnHide(visible, state.open)) closeAsk();
  }, [visible, state.open]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "k") return;
      const target = event.target as HTMLElement | null;
      const inAskField = target?.id === "ask-question";
      if (!inAskField && (isTypingTarget(target?.tagName) || target?.isContentEditable)) return;
      event.preventDefault();
      toggleAsk();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (!visible) return null;

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
          <AskPanel
            key={token}
            endpoint="/api/public/ask"
            suggestions={askSuggestionsAcross(groups ?? [])}
            initialQuestion={state.request?.question ?? ""}
            autoSend={state.request?.autoSend ?? false}
          />
        ) : null}
      </AskSheet>
    </>
  );
}
