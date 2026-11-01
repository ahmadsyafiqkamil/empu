import { redirect } from "next/navigation";

/** Ask is one global door now; old per-archive links land on it. */
export default function AskRedirect() {
  redirect("/ask");
}
