export const COPY = {
  tagline: "Capture what masters know, before it's gone.",
  home: {
    paragraph:
      "Empu turns a master's narrated work video into a watchable craft dictionary. Every term links to the original speech, a short clip of the movement, and the real tool, cropped from the original frame. AI proposes; a person decides.",
    fromArchive: "From the archive",
    archives: "Archives",
    openArchive: "Open the archive",
    tryClip: "Try it with a 3-minute clip",
    seeEvidence: "See the evidence",
    howItWorks: "How it works",
    principlesTitle: "Principles",
    comingSoon: "Coming next",
    steps: [
      "A master works and explains.",
      "Muse Spark 1.3 watches and listens; SAM 3.1 finds the tool.",
      "A person accepts, edits, or rejects. Only accepted terms go public.",
    ],
    principles: [
      "Evidence with every term.",
      "Every source labeled.",
      "Nothing public without a person's approval.",
      "Original frames only.",
    ],
    vision: "Batik today. Weaving and gamelan next. Every craft that was never written down.",
    frameAttribution:
      "Frames from \"Proses nyanting batik tulis\" by TEBAK teras batik kaindra and \"Macam Canting dalam Batik Tulis\" by Batik Education, both CC BY 3.0 on YouTube. Trimmed by Empu.",
  },
  source: {
    speech: "Spoken",
    on_screen_text: "On-screen text",
    visual_only: "Visual only",
  },
  sourceTooltip: {
    speech: "Heard in the recording's audio.",
    on_screen_text: "Read from text shown in the video, not spoken.",
    visual_only: "Seen in the video; not spoken or written.",
  },
  timeSource: {
    asr: "Timed by speech recognition",
    muse: "Timed by Muse",
  },
  timeSourceTooltip: {
    asr: "Muse found the term; the timestamp was aligned to a word-level transcript.",
    muse: "Timestamp from Muse; no transcript match.",
  },
  confidence: {
    high: "High confidence",
    medium: "Medium confidence",
    low: "Low confidence",
  },
  novel: {
    label: "New term",
    tooltip: "Not in this craft pack yet. Check with the maker.",
  },
  validation: {
    documenter: "Validated by the documenter",
    proposed: "Proposed by AI · not yet reviewed",
  },
  crop: {
    original: "Original frame · cropped with SAM 3.1",
    showInFrame: "Show in frame",
    showCrop: "Crop",
    noCrop: "No crop found · full frame shown",
  },
  ui: {
    hearIt: "Hear it",
    playing: "Playing…",
    clearFilters: "Clear filters",
    processMap: "Process map",
    downloadPublic: "Download (public)",
    noTerms: "No terms match these filters.",
    seeInProcessMap: "See where it sits in the process map →",
    browseProcessMaps: "Browse process maps",
  },
  attributionTrimmed: "Trimmed by Empu",
  studio: {
    accept: "Accept (A)",
    edit: "Edit (E)",
    reject: "Reject (R)",
    merge: "Merge…",
    next: "Next (J)",
    previous: "Previous (K)",
    saveEdit: "Save edit",
    cancel: "Cancel",
  },
  consent: {
    withdraw: "Withdraw consent for this recording",
    confirm:
      "All entries from this recording will disappear from the public dictionary and from exports. Files are kept but hidden. Withdraw consent?",
    checkbox:
      "I confirm the contributor granted permission to process this recording, and I recorded that consent.",
    public: "Public: accepted entries can appear in the public dictionary.",
    community: "Community: kept out of the public dictionary; visible in the studio.",
    private: "Private: restricted knowledge; never public.",
  },
  stages: {
    normalizing: "Preparing video",
    chunking: "Cutting 75-second segments",
    analyzing: "Muse Spark watches and listens",
    merging: "Matching terms to the craft pack",
    grounding: "SAM 3.1 finds the tools",
    cutting: "Cutting evidence clips",
    ready: "Ready to review",
  },
  try: {
    sandbox: "Your clip goes to a private sandbox. It is not listed publicly.",
  },
  evidence: {
    title: "This is the score, not the goal.",
    subtitle:
      "Measured against human-checked answer keys. We publish the real numbers, including the misses.",
    limitSource: "Source labels are weaker when captions are burnt into the video.",
    limitTime:
      "Timestamps are realigned with local speech recognition; spelling still comes from Muse.",
  },
  principle: "AI proposes. A person decides.",
  footer:
    "Built for the Meta Global AI Developer Hackathon 2026 with Muse Spark 1.3 and SAM 3.1. Demo clips are CC BY videos, credited on every entry.",
  empty: {
    dictionary: "No public entries yet. Terms appear here after a person accepts them.",
    entry404:
      "This entry isn't public. It may still be under review, or its recording's consent was withdrawn.",
    crop: "No crop found · full frame shown",
    clip: "Clip unavailable",
    studioFilter: "Nothing left in this filter.",
    showAccepted: "Show accepted",
    wrongKey: "Wrong key",
    quota: "Today's sandbox uploads are used up. The archive is still open to explore.",
    studioDesktop: "Studio works best on a desktop screen",
  },
  export: {
    note: "Every export includes creator attribution and the license.",
    publicOnly: "Public entries only",
    everything: "Everything except rejected (studio)",
  },
  ask: {
    title: "Ask the archive",
    intro:
      "Ask a question about this craft. Answers come only from terms a person has accepted, and every claim carries its clip, its tool and its timestamp.",
    placeholder: "Ask what a term means, or how a step is done…",
    submit: "Ask",
    thinking: "Looking through the archive…",
    refused: "This archive doesn't cover that yet. Try another term, or browse the dictionary.",
    rateLimited: "That's a lot of questions for one hour. Try again a little later.",
    unavailable: "The archive couldn't answer just now. Try again in a moment.",
    failed: "Something went wrong on the way to the archive. Try again.",
    evidence: "What this answer stands on",
    openEntry: "Open entry",
    studioNote: "Includes entries that are still under review.",
    launcher: "Ask",
    close: "Close",
    shortcut: "⌘K",
    askTerm: "Ask about this term",
    askArchive: "Ask the archive",
  },
};

/** Human-readable pipeline stage labels (desain.md). Do not paraphrase. */
export const STAGE_LABEL = COPY.stages;

export const CATEGORY_LABEL: Record<string, string> = {
  tool: "Tools",
  tool_part: "Tool parts",
  material: "Materials",
  dye: "Dyes",
  stage: "Stages",
  technique: "Techniques",
  motif: "Motifs",
  other: "Other",
};

export function expertValidationLabel(name: string): string {
  return `Validated by the expert · ${name}`;
}

export function studioReviewProgress(reviewed: number, total: number): string {
  return `${reviewed} of ${total} reviewed`;
}

export function mergePreview(from: string, into: string): string {
  return `Merge ${from} into ${into}?`;
}


export function attributionLine(parts: {
  title: string;
  creator: string;
  license: string;
  url: string;
}): string {
  return `From "${parts.title}" by ${parts.creator} · ${parts.license} · ${parts.url} · ${COPY.attributionTrimmed}`;
}

export function ensureTrimmedByEmpu(text: string): string {
  // The API already appends a trim note in some exports ("Trimmed by Empu",
  // "Trimmed and analyzed by Empu."). Never stack a second one.
  if (/trimmed/i.test(text)) return text;
  return `${text} · ${COPY.attributionTrimmed}`;
}
