export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-theme="malam" className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      {children}
    </div>
  );
}
