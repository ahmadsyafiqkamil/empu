/**
 * Open/close state for the Ask panel.
 *
 * Every trigger on the page (floating button, entry page, dictionary header)
 * calls `openAsk`; one panel listens. `token` changes on every open so the panel
 * can reset itself and start a fresh turn instead of stacking requests.
 */

export type AskRequest = {
  token: number;
  question: string;
  autoSend: boolean;
};

export type AskState = {
  open: boolean;
  request: AskRequest | null;
};

const INITIAL: AskState = { open: false, request: null };

let state: AskState = INITIAL;
let token = 0;
const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

export function subscribeAsk(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getAskSnapshot(): AskState {
  return state;
}

export function getAskServerSnapshot(): AskState {
  return INITIAL;
}

export function openAsk(question = "", opts: { autoSend?: boolean } = {}): void {
  token += 1;
  const trimmed = question.trim();
  state = {
    open: true,
    request: trimmed
      ? { token, question: trimmed, autoSend: opts.autoSend ?? false }
      : { token, question: "", autoSend: false },
  };
  emit();
}

export function closeAsk(): void {
  if (!state.open) return;
  state = { ...state, open: false };
  emit();
}

export function toggleAsk(): void {
  if (state.open) closeAsk();
  else openAsk();
}

/** Test helper: reset module state between cases. */
export function resetAskStore(): void {
  state = INITIAL;
  token = 0;
  emit();
}
