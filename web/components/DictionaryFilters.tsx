"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useRef } from "react";
import { CATEGORY_LABEL, COPY } from "@/lib/copy";

export type StageOption = { id: string; label: string };

const CATEGORIES = ["tool", "tool_part", "material", "dye", "stage", "technique", "motif", "other"];

export function DictionaryFilters({
  stages,
  q,
  category,
  stage,
  isNovel,
}: {
  stages: StageOption[];
  q: string;
  category: string;
  stage: string;
  isNovel: boolean;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function push(next: Record<string, string | null>) {
    const sp = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(next)) {
      if (value) sp.set(key, value);
      else sp.delete(key);
    }
    const s = sp.toString();
    router.replace(s ? `?${s}` : "?", { scroll: false });
  }

  function onText(value: string) {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => push({ q: value.trim() || null }), 350);
  }

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] items-center gap-3 border-b border-[var(--color-divider)] py-4 lg:grid-cols-[280px_minmax(0,1fr)_180px_auto]">
      <input
        key={q}
        className="input h-10"
        defaultValue={q}
        onChange={(e) => onText(e.target.value)}
        placeholder="Search terms, meanings…"
        aria-label="Search terms"
      />

      <div className="-mx-5 flex gap-1.5 overflow-x-auto px-5 lg:mx-0 lg:flex-wrap lg:overflow-visible lg:px-0">
        <button
          type="button"
          onClick={() => push({ category: null })}
          className="border px-3 py-[7px] text-[13px] whitespace-nowrap transition-colors"
          style={
            !category
              ? { background: "var(--color-text)", color: "var(--color-bg)", borderColor: "var(--color-text)" }
              : { borderColor: "var(--color-divider)" }
          }
        >
          All
        </button>
        {CATEGORIES.map((c) => {
          const on = category === c;
          return (
            <button
              key={c}
              type="button"
              onClick={() => push({ category: on ? null : c })}
              aria-pressed={on}
              className="border px-3 py-[7px] text-[13px] whitespace-nowrap transition-colors"
              style={
                on
                  ? { background: "var(--color-text)", color: "var(--color-bg)", borderColor: "var(--color-text)" }
                  : { borderColor: "var(--color-divider)" }
              }
            >
              {CATEGORY_LABEL[c] ?? c}
            </button>
          );
        })}
      </div>

      {stages.length > 0 ? (
        <select
          className="input h-10"
          value={stage}
          onChange={(e) => push({ stage: e.target.value || null })}
          aria-label="Stage"
        >
          <option value="">All stages</option>
          {stages.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      ) : (
        <span />
      )}

      <label className="flex cursor-pointer items-center gap-2 text-[13px] whitespace-nowrap">
        <input
          type="checkbox"
          checked={isNovel}
          onChange={(e) => push({ is_novel: e.target.checked ? "1" : null })}
          className="size-4 accent-[var(--color-accent)]"
        />
        New terms only
      </label>
    </div>
  );
}

export function ClearFiltersButton() {
  const router = useRouter();
  return (
    <button type="button" className="btn btn-secondary" onClick={() => router.replace("?")}>
      {COPY.ui.clearFilters}
    </button>
  );
}
