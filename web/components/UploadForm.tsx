"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";
import { cn } from "@/lib/cn";
import { COPY } from "@/lib/copy";
import type { Archive, SourceKind } from "@/lib/types";

const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;
const MAX_DURATION_S = 20 * 60;

function sourceKindLabel(kind: SourceKind): string {
  switch (kind) {
    case "own_recording":
      return "Own recording";
    case "cc_by_video":
      return "CC BY video";
    default: {
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }
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

export function UploadForm() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [archives, setArchives] = useState<Archive[]>([]);
  const [consent, setConsent] = useState(false);
  const [kind, setKind] = useState<SourceKind>("own_recording");
  const [error, setError] = useState<string | null>(null);
  const [fileLabel, setFileLabel] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [creatingArchive, setCreatingArchive] = useState(false);

  useEffect(() => {
    apiGet<Archive[]>("/api/archives")
      .then(setArchives)
      .catch((e) => setError(String(e)));
  }, []);

  const validateFile = useCallback(async (file: File): Promise<string | null> => {
    if (file.size > MAX_UPLOAD_BYTES) {
      return "Video must be 500 MB or smaller.";
    }
    try {
      const duration = await videoDurationSeconds(file);
      if (!Number.isFinite(duration) || duration > MAX_DURATION_S) {
        return "Video must be 20 minutes or shorter.";
      }
    } catch {
      return "Could not read video duration.";
    }
    return null;
  }, []);

  async function assignFile(file: File | null) {
    if (!file) {
      setFileLabel(null);
      return;
    }
    const problem = await validateFile(file);
    if (problem) {
      setError(problem);
      setFileLabel(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    setError(null);
    setFileLabel(file.name);
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
      const a = await apiSend<Archive>("/api/archives", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug: "demo", title: "Living Archive · Batik Tulis" }),
      });
      setArchives([a]);
    } catch (err) {
      setError(String(err));
    } finally {
      setCreatingArchive(false);
    }
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!consent || archives.length === 0) return;
    const fd = new FormData(e.currentTarget);
    fd.set("consent_confirmed", "true");
    fd.set("source_kind", kind);
    const file = fd.get("file");
    if (file instanceof File) {
      const problem = await validateFile(file);
      if (problem) {
        setError(problem);
        return;
      }
    }
    const archiveId = fd.get("archive_id");
    try {
      const res = await apiSend<{ recording_id: number; job_id: number }>(
        `/api/archives/${archiveId}/recordings`,
        { method: "POST", body: fd },
      );
      router.push(`/studio/jobs/${res.job_id}`);
    } catch (err) {
      setError(String(err));
    }
  }

  const hasArchive = archives.length > 0;

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-xl space-y-4 p-6">
      <h1 className="text-2xl">Upload recording</h1>
      {error && <p className="text-[var(--danger)]">{error}</p>}

      {!hasArchive ? (
        <div className="space-y-3 border border-[var(--line)] bg-[var(--surface)] p-4">
          <p className="text-sm text-[var(--muted)]">Create an archive before uploading a recording.</p>
          <button
            type="button"
            className="border border-[var(--line)] px-4 py-2 disabled:opacity-40"
            disabled={creatingArchive}
            onClick={() => void createDemoArchive()}
          >
            Create archive
          </button>
        </div>
      ) : (
        <>
          <label className="block text-sm">
            Archive
            <select
              name="archive_id"
              className="mt-1 w-full border border-[var(--line)] bg-transparent p-2"
              required
            >
              {archives.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title}
                </option>
              ))}
            </select>
          </label>

          <div className="block text-sm">
            <span>Video</span>
            <div
              className={cn(
                "mt-1 flex min-h-28 cursor-pointer flex-col items-center justify-center border border-dashed p-6 text-center",
                dragOver ? "border-[var(--wax)] bg-[var(--surface)]" : "border-[var(--line)]",
              )}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const file = e.dataTransfer.files.item(0);
                void assignFile(file);
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
              <p className="text-[var(--muted)]">
                {fileLabel ?? "Drop a video here or click to choose (max 500 MB, 20 minutes)"}
              </p>
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

          <label className="block text-sm">
            Title
            <input
              name="title"
              required
              className="mt-1 w-full border border-[var(--line)] bg-transparent p-2"
            />
          </label>
          <label className="block text-sm">
            Contributor name
            <input
              name="contributor_name"
              className="mt-1 w-full border border-[var(--line)] bg-transparent p-2"
            />
          </label>
          <label className="block text-sm">
            Location
            <input name="location" className="mt-1 w-full border border-[var(--line)] bg-transparent p-2" />
          </label>

          <fieldset className="space-y-2">
            <legend className="text-sm">Source</legend>
            <div className="flex border border-[var(--line)]">
              {(["own_recording", "cc_by_video"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  className={cn(
                    "flex-1 px-3 py-2 text-sm",
                    kind === value
                      ? "bg-[var(--accent)] text-black"
                      : "bg-transparent text-[var(--fg)]",
                  )}
                  onClick={() => setKind(value)}
                >
                  {sourceKindLabel(value)}
                </button>
              ))}
            </div>
          </fieldset>

          {kind === "cc_by_video" && (
            <div className="space-y-2 border border-[var(--line)] p-3">
              <input
                name="source_url"
                required
                placeholder="Source URL"
                className="w-full border border-[var(--line)] bg-transparent p-2"
              />
              <input
                name="source_creator"
                required
                placeholder="Creator"
                className="w-full border border-[var(--line)] bg-transparent p-2"
              />
              <input
                name="license"
                required
                defaultValue="CC BY 3.0"
                className="w-full border border-[var(--line)] bg-transparent p-2"
              />
              <textarea
                name="attribution"
                required
                placeholder="Attribution text"
                className="w-full border border-[var(--line)] bg-transparent p-2"
              />
            </div>
          )}

          <fieldset className="space-y-3 border border-[var(--wax)] bg-[var(--surface)] p-4">
            <legend className="text-sm font-medium">Consent</legend>
            <div className="space-y-2">
              <label className="block text-sm">
                <input type="radio" name="consent_scope" value="public" defaultChecked />{" "}
                {COPY.consent.public}
              </label>
              <label className="block text-sm">
                <input type="radio" name="consent_scope" value="community" /> {COPY.consent.community}
              </label>
              <label className="block text-sm">
                <input type="radio" name="consent_scope" value="private" /> {COPY.consent.private}
              </label>
            </div>
            <label className="block text-sm">
              Consent note
              <input
                name="consent_note"
                className="mt-1 w-full border border-[var(--line)] bg-transparent p-2"
              />
            </label>
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              {COPY.consent.checkbox}
            </label>
          </fieldset>

          <button
            disabled={!consent}
            className="bg-[var(--accent)] px-4 py-2 text-black disabled:opacity-40"
          >
            Upload and process
          </button>
        </>
      )}
    </form>
  );
}
