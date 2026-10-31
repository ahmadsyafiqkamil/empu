# Poles Ask Empu untuk Demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menghilangkan empat gesekan yang paling mungkin muncul saat merekam demo: panel yang terbuka dingin tanpa contoh pertanyaan, galat yang tidak bisa diulang, panel yang membuka sendiri saat kembali dari Studio, dan `⌘K` yang membajak kolom pencarian.

**Architecture:** Panel dan tombol melayang sudah ada (`AskPanel`, `AskLauncher`, `askStore`). Yang ditambahkan hanya: chip contoh pertanyaan di dalam panel (memakai `askSuggestions` yang sudah ada), tombol "Try again" yang mengirim ulang pertanyaan terakhir, penutupan panel saat tombol melayang tidak lagi ditampilkan, dan penjaga fokus untuk pintasan `⌘K`. Keputusan yang bisa diuji diekstrak ke `web/lib/askUi.ts`; sisanya komponen tanpa jsdom, jadi diverifikasi manual.

**Tech Stack:** Next.js 16.4 (App Router), React 19, TypeScript, vitest (`environment: "node"`, tanpa jsdom).

**Spec:** `docs/superpowers/specs/2026-10-31-ask-empu-design.md` bagian 9.5 (UI) dan `/Users/ahmadsyafiqkamil/.opencode/plan/2026-10-31-ask-empu-ui-placement.md` bagian 3.

## Global Constraints

- UI bahasa Inggris; istilah keahlian tetap asli. Copy baru masuk `web/lib/copy.ts`, jangan diparafrase di komponen.
- Tanpa warna, radius, atau bayangan baru. Hanya token `globals.css` dan kelas yang sudah ada (`.btn`, `.btn-secondary`, `.empty`, `.label`).
- Tanpa `window.alert` / `window.prompt`.
- Satu pertanyaan sekaligus: tombol kirim nonaktif saat menunggu, dan `Enter` tidak boleh mengirim dua kali.
- Tes frontend hanya untuk fungsi murni (`vitest` node env). Perilaku komponen diverifikasi manual dengan checklist yang tertulis di task.
- Lint harus bersih; aturan `react-hooks/set-state-in-effect` tidak boleh dimatikan kecuali di tempat yang sudah ada komentarnya.

## Review Focus

1. **Panel terbuka dingin.** Saat direkam, panel kosong tanpa saran membuat presenter harus mengetik; satu salah ketik langsung terlihat. (Task 1)
2. **Galat buntu.** 502/429 hanya menampilkan kalimat; tidak ada jalan mengulang tanpa mengetik ulang. (Task 2)
3. **Panel membuka sendiri.** Buka panel → pindah ke Studio → kembali ke halaman publik: panel terbuka tanpa diminta, dan bila permintaan terakhir `autoSend`, pertanyaannya terkirim ulang. (Task 3)
4. **`⌘K` membajak input.** Di halaman kamus, `⌘K` milik kolom pencarian. (Task 4)
5. **Saran yang membocorkan istilah belum tervalidasi.** Chip dibangun dari daftar entri publik; jangan pernah mengambilnya dari `scope=studio`. (Task 1)

---

## File Map

| File | Aksi | Tanggung jawab |
|---|---|---|
| `web/lib/askUi.ts` | Modify | `isTypingTarget`, `shouldCloseOnHide` |
| `web/lib/askUi.test.ts` | Modify | Tes dua helper baru |
| `web/lib/copy.ts` | Modify | `ask.retry`, `ask.suggestions` |
| `web/components/AskPanel.tsx` | Modify | Chip saran, tombol ulangi |
| `web/components/AskLauncher.tsx` | Modify | Ambil saran saat panel dibuka, tutup saat disembunyikan, penjaga `⌘K` |

---

### Task 1: Chip contoh pertanyaan di dalam panel

**Files:**
- Modify: `web/components/AskLauncher.tsx`

**Interfaces:**
- Consumes: `askSuggestions(entries, n=3) -> string[]` (sudah ada dan sudah diuji), prop `AskPanel.suggestions?: string[]` (sudah ada)
- Produces: `AskLauncher` mengirim `suggestions` hasil `askSuggestions(terms)` ke `AskPanel`

Perilaku (dipin): saat `state.open` menjadi `true` dan `terms` masih kosong, ambil `GET /api/public/archives/{slug}/entries` **sekali per slug**, simpan `terms`, lalu kirim `askSuggestions(terms)`. Kegagalan fetch → panel tetap terbuka tanpa chip; jangan tampilkan galat.

**Catatan TDD:** tidak ada logika murni baru di task ini — `askSuggestions` sudah diuji di `web/lib/askUi.test.ts` dan komponen tidak punya harness (vitest proyek ini `environment: "node"`, tanpa jsdom). Karena itu task ini tidak diawali tes baru; verifikasinya manual dengan checklist di Step 3. Jangan menambahkan dependensi jsdom hanya untuk ini.

- [ ] **Step 1: Implementasikan di `AskLauncher`**

State `terms: string[]`. `useEffect` pada `[state.open, slug]`: bila `open` dan `slug` dan `terms` kosong → `fetch("/api/public/archives/" + slug + "/entries")` → `.then()` → `setTerms(rows.map(r => r.term))`. SetState hanya di dalam `.then` (aturan `react-hooks/set-state-in-effect`). Lewatkan `suggestions={askSuggestions(terms)}` ke `AskPanel`. Ambil entri dari endpoint **publik**; jangan pernah dari `/api/archives/...`.

- [ ] **Step 2: Verifikasi build**

Run: `cd web && pnpm lint && pnpm test && pnpm build`
Expected: lolos.

- [ ] **Step 3: Verifikasi manual**

Buka `http://localhost:3000/d/batik-tulis`, klik tombol **Ask**.
Expected: panel menampilkan tiga chip di bawah kotak tanya. Klik satu chip → pertanyaan terkirim, chip hilang selama menunggu. Buka panel di `/map` (tanpa slug di URL) → chip tetap muncul setelah arsip demo ter-resolve.

- [ ] **Step 4: Commit**

```bash
git add web/components/AskLauncher.tsx
git commit -m "feat(ask): offer example questions inside the sheet"
```

---

### Task 2: Tombol ulangi setelah galat

**Files:**
- Modify: `web/components/AskPanel.tsx`, `web/lib/copy.ts`

**Interfaces:**
- Produces: `COPY.ask.retry = "Try again"`

Perilaku (dipin): ketika sebuah giliran berakhir dengan `error`, tampilkan `.empty` berisi pesan galat **dan** tombol `.btn .btn-secondary` berlabel `COPY.ask.retry`. Menekannya memanggil `send(turn.question)` yang sama; tombol nonaktif selama `pending`.

- [ ] **Step 1: Implementasikan**

Di blok `turn.error`, setelah `<span>{turn.error}</span>`, tambahkan tombol yang memanggil `send(turn.question)`. Jangan mengubah `turn` yang sudah ada; `send` menambah giliran baru — itu disengaja, agar riwayat memperlihatkan percobaan sebelumnya.

- [ ] **Step 2: Verifikasi**

Run: `cd web && pnpm lint && pnpm test && pnpm build`
Expected: lolos.

Manual, dengan API dimatikan sementara:
1. Buka panel, kirim pertanyaan → muncul `COPY.ask.failed` + tombol **Try again**.
2. Nyalakan API, klik **Try again** → giliran baru muncul dan dijawab.
3. Klik **Try again** dua kali cepat → hanya satu permintaan (tombol nonaktif saat `pending`).

- [ ] **Step 3: Commit**

```bash
git add web/components/AskPanel.tsx web/lib/copy.ts
git commit -m "feat(ask): retry a failed question without retyping it"
```

---

### Task 3: Tutup panel saat tombol melayang disembunyikan

**Files:**
- Modify: `web/lib/askUi.ts`, `web/lib/askUi.test.ts`, `web/components/AskLauncher.tsx`

**Interfaces:**
- Produces: `shouldCloseOnHide(visible: boolean, open: boolean) -> boolean` — `true` hanya bila `visible === false` dan `open === true`

- [ ] **Step 1: Tulis tes yang gagal**

```ts
it("closes the sheet when the launcher is no longer shown", () => {
  expect(shouldCloseOnHide(false, true)).toBe(true);
  expect(shouldCloseOnHide(false, false)).toBe(false);
  expect(shouldCloseOnHide(true, true)).toBe(false);
});
```

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd web && pnpm test -- askUi`
Expected: FAIL — `shouldCloseOnHide is not a function`.

- [ ] **Step 3: Implementasikan**

Tambahkan helper murni di `askUi.ts`. Di `AskLauncher`, `useEffect(() => { if (shouldCloseOnHide(visible, state.open)) closeAsk(); }, [visible, state.open])`.

- [ ] **Step 4: Verifikasi**

Run: `cd web && pnpm lint && pnpm test && pnpm build`
Expected: lolos.

Manual: buka panel di `/d/batik-tulis` → klik nav **Documenter studio** → kembali ke `/d/batik-tulis`. Panel **tidak** boleh terbuka sendiri, dan tidak ada permintaan baru di tab Network.

- [ ] **Step 5: Commit**

```bash
git add web/lib/askUi.ts web/lib/askUi.test.ts web/components/AskLauncher.tsx
git commit -m "fix(ask): do not reopen the sheet after leaving for the studio"
```

---

### Task 4: `⌘K` tidak membajak kolom isian

**Files:**
- Modify: `web/lib/askUi.ts`, `web/lib/askUi.test.ts`, `web/components/AskLauncher.tsx`

**Interfaces:**
- Produces: `isTypingTarget(tagName: string | null | undefined) -> boolean` — `true` untuk `INPUT`, `TEXTAREA`, `SELECT`, dan elemen `contentEditable` (ditandai oleh pemanggil dengan `(target as HTMLElement).isContentEditable`)

- [ ] **Step 1: Tulis tes yang gagal**

```ts
it("does not steal the shortcut from a text field", () => {
  expect(isTypingTarget("INPUT")).toBe(true);
  expect(isTypingTarget("textarea")).toBe(true);
  expect(isTypingTarget("SELECT")).toBe(true);
  expect(isTypingTarget("DIV")).toBe(false);
  expect(isTypingTarget(null)).toBe(false);
});
```

- [ ] **Step 2: Jalankan untuk memastikan gagal**

Run: `cd web && pnpm test -- askUi`
Expected: FAIL — `isTypingTarget is not a function`.

- [ ] **Step 3: Implementasikan**

Bandingkan `tagName.toUpperCase()` dengan `INPUT`/`TEXTAREA`/`SELECT`. Di handler `keydown`, lewati pintasan bila `isTypingTarget((event.target as HTMLElement | null)?.tagName)` **atau** `(event.target as HTMLElement | null)?.isContentEditable`. Kecuali: bila target adalah `#ask-question` di dalam panel, `⌘K` tetap menutup panel.

- [ ] **Step 4: Verifikasi**

Run: `cd web && pnpm lint && pnpm test && pnpm build`
Expected: lolos.

Manual: fokus ke kolom pencarian di `/d/batik-tulis`, tekan `⌘K` → panel **tidak** terbuka. Klik di area kosong halaman, tekan `⌘K` → panel terbuka.

- [ ] **Step 5: Commit**

```bash
git add web/lib/askUi.ts web/lib/askUi.test.ts web/components/AskLauncher.tsx
git commit -m "fix(ask): leave the keyboard shortcut to focused inputs"
```
