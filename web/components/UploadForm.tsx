"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Stepper } from "@/components/Stepper";
import { apiGet, apiSend } from "@/lib/api";
import { COPY } from "@/lib/copy";
import type { Archive, Pack, SourceKind } from "@/lib/types";

const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;
const MAX_DURATION_S = 20 * 60;
const TRY_MAX_DURATION_S = 3 * 60;

const STEPS = [{ label: "Upload" }, { label: "Process" }, { label: "Review in Studio" }];

function durationLabel(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function sizeLabel(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function videoDurationSeconds(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(video.duration);
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read video duration"));
    };
    video.src = url;
  });
}

export function UploadForm({ variant = "studio" }: { variant?: "studio" | "try" }) {
  const isTry = variant === "try";
  const maxDuration = isTry ? TRY_MAX_DURATION_S : MAX_DURATION_S;
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [archives, setArchives] = useState<Archive[]>([]);
  const [packs, setPacks] = useState<Pack[]>([]);
  const [consent, setConsent] = useState(false);
  const [kind, setKind] = useState<SourceKind>("own_recording");
  const [scope, setScope] = useState<"public" | "community" | "private">("public");
  const [error, setError] = useState<string | null>(null);
  const [picked, setPicked] = useState<{ name: string; size: number; duration: number } | null>(
    null,
  );
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [creatingArchive, setCreatingArchive] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newSlug, setNewSlug] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newPackId, setNewPackId] = useState("");

  useEffect(() => {
    if (isTry) return;
    apiGet<Archive[]>("/api/archives")
      .then(setArchives)
      .catch((e) => setError(String(e)));
  }, [isTry]);

  useEffect(() => {
    if (isTry) return;
    apiGet<Pack[]>("/api/packs")
      .then((ps) => {
        setPacks(ps);
        if (ps.length > 0) setNewPackId(ps[0].id);
      })
      .catch(() => setPacks([]));
  }, [isTry]);

  const validateFile = useCallback(
    async (file: File): Promise<string | null> => {
      if (file.size > MAX_UPLOAD_BYTES) return "Video must be 500 MB or smaller.";
      try {
        const duration = await videoDurationSeconds(file);
        if (!Number.isFinite(duration)) return "Could not read video duration.";
        if (duration > maxDuration) {
          return isTry ? "Video must be 3 minutes or shorter." : "Video must be 20 minutes or shorter.";
        }
        setPicked({ name: file.name, size: file.size, duration });
      } catch {
        return "Could not read video duration.";
      }
      return null;
    },
    [isTry, maxDuration],
  );

  async function assignFile(file: File | null) {
    if (!file) {
      setPicked(null);
      return;
    }
    const problem = await validateFile(file);
    if (problem) {
      setError(problem);
      setPicked(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    setError(null);
    const input = fileInputRef.current;
    if (input) {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
    }
  }

  async function createDemoArchive() {
    setCreatingArchive(true);
    setError(null);
    try {
      const pack = packs.find((p) => p.id === newPackId) ?? packs[0];
      const slug = newSlug.trim() || pack?.id || "demo";
      const title =
        newTitle.trim() || (pack ? `Living Archive · ${pack.name.id}` : "Living Archive");
      const a = await apiSend<Archive>("/api/archives", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, title, craft_pack_id: pack?.id ?? "" }),
      });
      setArchives((prev) => [...prev, a]);
      setShowCreate(false);
      setNewSlug("");
      setNewTitle("");
    } catch (err) {
      setError(String(err));
    } finally {
      setCreatingArchive(false);
    }
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!consent || busy) return;
    if (!isTry && archives.length === 0) return;
    const fd = new FormData(e.currentTarget);
    const file = fd.get("file");
    if (file instanceof File) {
      const problem = await validateFile(file);
      if (problem) {
        setError(problem);
        return;
      }
    }
    setBusy(true);
    try {
      if (isTry) {
        const body = new FormData();
        if (file instanceof File) body.append("file", file);
        body.append("title", String(fd.get("title") ?? ""));
        body.append("consent_confirmed", "true");
        const res = await apiSend<{ recording_id: number; job_id: number }>(
          "/api/sandbox/recordings",
          { method: "POST", body },
        );
        router.push(`/studio/jobs/${res.job_id}`);
        return;
      }
      fd.set("consent_confirmed", "true");
      fd.set("source_kind", kind);
      fd.set("consent_scope", scope);
      const archiveId = fd.get("archive_id");
      const res = await apiSend<{ recording_id: number; job_id: number }>(
        `/api/archives/${archiveId}/recordings`,
        { method: "POST", body: fd },
      );
      router.push(`/studio/jobs/${res.job_id}`);
    } catch (err) {
      setError(String(err));
      setBusy(false);
    }
  }

  const fileBox = (
    <div className="field">
      <span className="field-label">Video</span>
      <div
        className={
          dragOver
            ? "grid cursor-pointer grid-cols-[44px_minmax(0,1fr)] items-center gap-4 border-2 border-dashed border-[var(--color-accent)] bg-[var(--color-surface)] p-4"
            : "grid cursor-pointer grid-cols-[44px_minmax(0,1fr)] items-center gap-4 border-2 border-dashed border-[var(--color-divider)] bg-[var(--color-surface)] p-4 hover:border-[var(--color-text)]"
        }
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          void assignFile(e.dataTransfer.files.item(0));
        }}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={0}
      >
        <div
          className="grid size-11 place-items-center"
          style={{ background: "var(--color-text)", color: "var(--color-bg)" }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden
          >
            <path d="M12 3v12M7 8l5-5 5 5M21 21H3" />
          </svg>
        </div>
        <div className="min-w-0">
          {picked ? (
            <>
              <div className="mono truncate text-[15px] font-semibold">{picked.name}</div>
              <div className="text-[12px] text-[var(--color-neutral-700)]">
                {durationLabel(picked.duration)} · {sizeLabel(picked.size)} · ready to upload
              </div>
            </>
          ) : (
            <>
              <div className="text-[15px] font-semibold">
                Drop a video here, or click to choose
              </div>
              <div className="text-[12px] text-[var(--color-neutral-700)]">
                {isTry ? "Up to 3 minutes." : "Max 500 MB, 20 minutes."}
              </div>
            </>
          )}
        </div>
      </div>
      <input
        ref={fileInputRef}
        name="file"
        type="file"
        accept="video/*"
        required
        className="sr-only"
        onChange={(e) => void assignFile(e.target.files?.item(0) ?? null)}
      />
    </div>
  );

  const consentPanel = (
    <div className="flex flex-col gap-5 bg-[var(--color-surface)] px-5 py-8 lg:px-10 lg:py-12">
      <div>
        <div className="label font-extrabold text-[var(--color-accent-700)]">Required</div>
        <h2 className="mt-1 mb-0 text-[24px] lg:text-[28px]">Consent</h2>
        <p className="mt-1.5 mb-0 text-[14px] text-[var(--color-neutral-800)]">
          {isTry
            ? "A sandbox clip is private by default: nobody but you can see it, and it never enters the public dictionary."
            : "Choose who may see entries from this recording. You can withdraw consent later from the Studio."}
        </p>
      </div>

      {isTry ? (
        <div className="flex flex-col gap-2 border-t-2 border-[var(--color-divider)] pt-4 text-[14px]">
          <div className="flex items-center justify-between">
            <span className="text-[var(--color-neutral-700)]">Visibility</span>
            <span className="font-semibold">Private sandbox</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[var(--color-neutral-700)]">Max length</span>
            <span className="font-semibold">3 minutes</span>
          </div>
        </div>
      ) : (
        <div className="flex flex-col border-t-2 border-[var(--color-divider)]">
          {(
            [
              { id: "public", title: "Public", desc: "Accepted entries can appear in the public dictionary." },
              { id: "community", title: "Community", desc: "Kept out of the public dictionary; visible in the studio." },
              { id: "private", title: "Private", desc: "Restricted knowledge; never public." },
            ] as const
          ).map((opt) => (
            <label
              key={opt.id}
              className="flex cursor-pointer items-start gap-3 border-b border-[var(--color-divider)] px-1 py-4"
            >
              <input
                type="radio"
                name="consent_scope"
                value={opt.id}
                checked={scope === opt.id}
                onChange={() => setScope(opt.id)}
                className="mt-1 accent-[var(--color-accent)]"
              />
              <span className="flex flex-col">
                <b className="text-[15px]">{opt.title}</b>
                <span className="text-[13px] text-[var(--color-neutral-800)]">{opt.desc}</span>
              </span>
            </label>
          ))}
        </div>
      )}

      {!isTry ? (
        <label className="field">
          <span className="field-label">Consent note</span>
          <textarea
            name="consent_note"
            className="input"
            placeholder="How and when permission was given"
          />
        </label>
      ) : null}

      <label
        className="grid cursor-pointer grid-cols-[20px_1fr] items-start gap-3 border-2 bg-[var(--color-bg)] p-4"
        style={{
          borderColor: consent ? "var(--color-text)" : "var(--color-accent)",
        }}
      >
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5 size-[18px] accent-[var(--color-accent)]"
        />
        <span className="text-[14px] leading-snug">{COPY.consent.checkbox}</span>
      </label>

      <button
        type="submit"
        disabled={!consent || busy}
        className="btn btn-primary h-[52px] justify-start px-5 text-base"
      >
        {busy ? "Uploading…" : isTry ? "Process 3-minute clip" : "Upload and process"}
        <span className="ml-auto" aria-hidden>
          →
        </span>
      </button>
      {!consent ? (
        <p className="-mt-3 mb-0 text-[12px] text-[var(--color-accent-700)]">
          Tick the consent box to continue.
        </p>
      ) : null}
    </div>
  );

  if (isTry) {
    return (
      <form onSubmit={onSubmit} className="grid grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)_520px]">
        <div className="flex flex-col gap-6 px-5 py-8 lg:px-14 lg:py-12">
          <div>
            <h1 className="m-0 text-[32px] tracking-[-0.02em] lg:text-[42px]">Try it</h1>
            <p className="mt-1 mb-0 text-[14px] text-[var(--color-neutral-800)]">
              {COPY.try.sandbox}
            </p>
          </div>
          {error ? <p className="text-[13px] text-[var(--color-accent-700)]">{error}</p> : null}
          {fileBox}
          <label className="field">
            <span className="field-label">Title</span>
            <input name="title" required className="input h-11" placeholder="What is this clip?" />
          </label>
        </div>
        {consentPanel}
      </form>
    );
  }

  return (
    <form onSubmit={onSubmit}>
      <Stepper steps={STEPS} active={0} />
      <div className="grid grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)_520px]">
        <div className="flex flex-col gap-6 border-[var(--color-divider)] px-5 py-8 lg:border-r-2 lg:px-14 lg:py-12">
          <h1 className="m-0 text-[32px] tracking-[-0.02em] lg:text-[42px]">Upload recording</h1>
          {error ? <p className="text-[13px] text-[var(--color-accent-700)]">{error}</p> : null}

          {showCreate || archives.length === 0 ? (
            <div className="flex flex-col gap-3 border-2 border-[var(--color-divider)] p-4">
              <p className="m-0 text-[13px] text-[var(--color-neutral-800)]">
                Create a new archive.
              </p>
              <label className="field">
                <span className="field-label">Archive slug</span>
                <input
                  value={newSlug}
                  onChange={(e) => setNewSlug(e.target.value)}
                  placeholder="gamelan"
                  className="input h-11"
                />
              </label>
              <label className="field">
                <span className="field-label">Title</span>
                <input
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Living Archive · Gamelan"
                  className="input h-11"
                />
              </label>
              <label className="field">
                <span className="field-label">Craft pack</span>
                <select
                  value={newPackId}
                  onChange={(e) => setNewPackId(e.target.value)}
                  className="input h-11"
                >
                  {packs.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name.id}
                    </option>
                  ))}
                </select>
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={creatingArchive || packs.length === 0}
                  onClick={() => void createDemoArchive()}
                >
                  {creatingArchive ? "Creating…" : "Create archive"}
                </button>
                {archives.length > 0 ? (
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setShowCreate(false)}
                  >
                    Cancel
                  </button>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-[minmax(0,1fr)] items-end gap-3 md:grid-cols-[1fr_auto]">
              <label className="field">
                <span className="field-label">Archive</span>
                <select name="archive_id" required className="input h-11">
                  {archives.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.title}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="btn btn-secondary h-11"
                onClick={() => setShowCreate(true)}
              >
                + Create new archive
              </button>
            </div>
          )}

          {fileBox}

          <label className="field">
            <span className="field-label">Title</span>
            <input name="title" required className="input h-11" placeholder="e.g. Gamelan part 2" />
          </label>

          <div className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
            <label className="field">
              <span className="field-label">Contributor name</span>
              <input name="contributor_name" className="input h-11" />
            </label>
            <label className="field">
              <span className="field-label">Location</span>
              <input name="location" className="input h-11" placeholder="Village, region" />
            </label>
          </div>

          <div className="field">
            <span className="field-label">Source</span>
            <div className="seg w-full">
              <label className="seg-opt h-11 flex-1 justify-center text-sm">
                <input
                  type="radio"
                  name="source_kind"
                  checked={kind === "own_recording"}
                  onChange={() => setKind("own_recording")}
                />
                Own recording
              </label>
              <label className="seg-opt h-11 flex-1 justify-center text-sm">
                <input
                  type="radio"
                  name="source_kind"
                  checked={kind === "cc_by_video"}
                  onChange={() => setKind("cc_by_video")}
                />
                CC BY video
              </label>
            </div>
          </div>

          {kind === "cc_by_video" ? (
            <div className="grid grid-cols-[minmax(0,1fr)] gap-3 border-2 border-[var(--color-divider)] p-4">
              <label className="field">
                <span className="field-label">Source URL</span>
                <input name="source_url" required className="input h-11" />
              </label>
              <label className="field">
                <span className="field-label">Creator</span>
                <input name="source_creator" required className="input h-11" />
              </label>
              <label className="field">
                <span className="field-label">License</span>
                <input name="license" required defaultValue="CC BY 3.0" className="input h-11" />
              </label>
              <label className="field">
                <span className="field-label">Attribution text</span>
                <textarea name="attribution" required className="input" />
              </label>
            </div>
          ) : null}
        </div>

        {consentPanel}
      </div>
    </form>
  );
}
