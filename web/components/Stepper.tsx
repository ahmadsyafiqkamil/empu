export type Step = {
  label: string;
  href?: string;
};

export function Stepper({
  steps,
  active,
  done,
}: {
  steps: Step[];
  active: number;
  done?: number[];
}) {
  return (
    <ol className="grid grid-cols-[minmax(0,1fr)] border-b-2 border-[var(--color-divider)] text-[13px] md:grid-cols-3">
      {steps.map((step, i) => {
        const isActive = i === active;
        const isDone = done?.includes(i) ?? false;
        const cell = (
          <span className="flex items-center gap-2">
            <b className={isActive || isDone ? "" : "font-normal text-[var(--color-neutral-700)]"}>
              {String(i + 1).padStart(2, "0")}
            </b>
            <span className={isActive ? "font-semibold" : "text-[var(--color-neutral-700)]"}>
              {step.label}
            </span>
            {isDone ? <span aria-hidden>✓</span> : null}
          </span>
        );
        return (
          <li
            key={step.label}
            className={
              isActive
                ? "border-b-[3px] border-[var(--color-accent)] bg-[var(--color-surface)] px-4 py-3.5 md:border-b-0 md:border-r md:border-[var(--color-divider)] md:shadow-[inset_0_-3px_0_var(--color-accent)]"
                : "border-b border-[var(--color-divider)] px-4 py-3.5 md:border-b-0 md:border-r md:border-[var(--color-divider)] last:md:border-r-0"
            }
          >
            {step.href && !isActive ? (
              <a href={step.href} className="text-[var(--color-text)] no-underline">
                {cell}
              </a>
            ) : (
              cell
            )}
          </li>
        );
      })}
    </ol>
  );
}
