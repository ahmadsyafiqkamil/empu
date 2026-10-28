const KEY_STORAGE = "empu.studioKey";

export function getStudioKey(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(KEY_STORAGE) ?? process.env.NEXT_PUBLIC_STUDIO_KEY ?? "";
}

export function setStudioKey(key: string) {
  if (key) sessionStorage.setItem(KEY_STORAGE, key);
  else sessionStorage.removeItem(KEY_STORAGE);
}

export function studioHeaders(extra?: HeadersInit): Headers {
  const h = new Headers(extra);
  const key = getStudioKey();
  if (key) h.set("X-Studio-Key", key);
  return h;
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(path, { headers: studioHeaders(), cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export async function apiSend<T>(path: string, init: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, headers: studioHeaders(init.headers) });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export function mediaSrc(url: string | null | undefined): string | undefined {
  return url ?? undefined;
}
