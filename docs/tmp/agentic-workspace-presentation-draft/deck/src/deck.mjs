/** @jsxRuntime automatic */
/** @jsxImportSource @oai/artifact-tool/presentation-jsx */

const {
  Presentation,
  PresentationFile,
  row,
  column,
  grid,
  text,
  rule,
  fill,
  hug,
  fixed,
  wrap,
  grow,
  fr,
  auto,
} = await import("@oai/artifact-tool");
const fs = await import("node:fs/promises");

const W = 1920;
const H = 1080;
const OUT = "output/output.pptx";
const SCRATCH = "scratch";

async function saveBlob(blob, path) {
  const buffer = Buffer.from(await blob.arrayBuffer());
  await fs.writeFile(path, buffer);
}

const colors = {
  ink: "#111827",
  muted: "#475569",
  faint: "#CBD5E1",
  line: "#E2E8F0",
  teal: "#0F766E",
  blue: "#2563EB",
  amber: "#B45309",
  purple: "#6D28D9",
  red: "#B91C1C",
};

const font = "Aptos";
const mono = "Aptos Mono";

function titleStyle(size = 60, color = colors.ink) {
  return { fontFace: font, fontSize: size, bold: true, color, lineSpacingMultiple: 0.92 };
}

function bodyStyle(size = 28, color = colors.muted) {
  return { fontFace: font, fontSize: size, color, lineSpacingMultiple: 1.14 };
}

function labelStyle(size = 17, color = colors.teal) {
  return { fontFace: mono, fontSize: size, bold: true, color, characterSpacing: 0.8 };
}

function addSlide(presentation, children, name = "slide") {
  const slide = presentation.slides.add();
  slide.compose(
    column(
      { name: `${name}-root`, width: fill, height: fill, padding: { x: 92, y: 70 }, gap: 28 },
      children,
    ),
    { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 },
  );
  return slide;
}

function header(kicker, title, subtitle, accent = colors.teal) {
  return column(
    { name: "header", width: fill, height: hug, gap: 16 },
    [
      text(kicker.toUpperCase(), {
        name: "kicker",
        width: fill,
        height: hug,
        style: labelStyle(16, accent),
      }),
      text(title, {
        name: "slide-title",
        width: wrap(1450),
        height: fixed(136),
        style: titleStyle(56),
      }),
      subtitle
        ? text(subtitle, {
            name: "slide-subtitle",
            width: wrap(1320),
            height: fixed(54),
            style: bodyStyle(26),
          })
        : rule({ name: "title-rule", width: fixed(280), stroke: accent, weight: 5 }),
    ].filter(Boolean),
  );
}

function footer(textValue) {
  return text(textValue, {
    name: "footer",
    width: fill,
    height: hug,
    style: { fontFace: font, fontSize: 15, color: "#94A3B8" },
  });
}

function bullets(items, size = 30, color = colors.ink, width = 1320) {
  return column(
    { name: "bullet-list", width: fixed(width), height: hug, gap: 16 },
    items.map((item, index) =>
      row(
        { name: `bullet-${index}`, width: fixed(width), height: hug, gap: 18 },
        [
          text("—", {
            name: `bullet-mark-${index}`,
            width: fixed(30),
            height: hug,
            style: { fontFace: font, fontSize: size, color: colors.teal, bold: true },
          }),
          text(item, {
            name: `bullet-text-${index}`,
            width: fixed(width - 48),
            height: hug,
            style: bodyStyle(size, color),
          }),
        ],
      ),
    ),
  );
}

function openList(label, items, accent = colors.teal, width = 650, size = 27) {
  return column(
    { name: `${label}-list`, width: fixed(width), height: hug, gap: 14 },
    [
      text(label.toUpperCase(), {
        name: `${label}-label`,
        width: fixed(width),
        height: hug,
        style: labelStyle(16, accent),
      }),
      ...items.map((item, index) =>
        row(
          { name: `${label}-row-${index}`, width: fixed(width), height: hug, gap: 12 },
          [
            text("—", {
              name: `${label}-mark-${index}`,
              width: fixed(24),
              height: hug,
              style: { fontFace: font, fontSize: size, bold: true, color: accent },
            }),
            text(item, {
              name: `${label}-item-${index}`,
              width: fixed(width - 42),
              height: hug,
              style: bodyStyle(size, colors.ink),
            }),
          ],
        ),
      ),
    ],
  );
}

function arrowStep(label, detail, accent = colors.teal) {
  return column(
    { name: `${label}-step`, width: fill, height: hug, gap: 10 },
    [
      text(label, {
        name: `${label}-step-label`,
        width: fill,
        height: hug,
        style: { fontFace: font, fontSize: 31, bold: true, color: accent },
      }),
      text(detail, {
        name: `${label}-step-detail`,
        width: wrap(280),
        height: hug,
        style: bodyStyle(20, colors.muted),
      }),
    ],
  );
}

function splitColumns(left, right, ratio = [fr(1), fr(1)]) {
  return grid(
    {
      name: "split-columns",
      width: fill,
      height: fill,
      columns: ratio,
      rows: [fr(1)],
      columnGap: 70,
    },
    [left, right],
  );
}

function bigQuote(main, sub, accent = colors.teal, width = 1420, mainSize = 58, subSize = 28) {
  return column(
    { name: "big-quote", width: fixed(width), height: hug, gap: 24 },
    [
      rule({ name: "quote-rule", width: fixed(320), stroke: accent, weight: 7 }),
      text(main, {
        name: "big-quote-main",
        width: fixed(width),
        height: hug,
        style: titleStyle(mainSize, colors.ink),
      }),
      text(sub, {
        name: "big-quote-sub",
        width: fixed(Math.min(width, 1220)),
        height: hug,
        style: bodyStyle(subSize),
      }),
    ],
  );
}

const presentation = Presentation.create({
  slideSize: { width: W, height: H },
});

// 1. Cover
addSlide(
  presentation,
  [
    text("AGENTIC WORKSPACE", {
      name: "cover-kicker",
      width: fill,
      height: hug,
      style: labelStyle(18, colors.teal),
    }),
    column(
      { name: "cover-lockup", width: fill, height: grow(1), gap: 34 },
      [
        text("Making agent work survive time", {
          name: "cover-title",
          width: wrap(1420),
          height: hug,
          style: titleStyle(82),
        }),
        text("A repo-native operating layer for intent, context, proof, ownership, and handoff.", {
          name: "cover-subtitle",
          width: wrap(1060),
          height: hug,
          style: bodyStyle(32),
        }),
        rule({ name: "cover-rule", width: fixed(520), stroke: colors.teal, weight: 8 }),
      ],
    ),
    footer("Draft structure for a developer audience"),
  ],
  "cover",
);

// 2. Why
addSlide(
  presentation,
  [
    header(
      "Why",
      "AI coding tools are fast, but weak at continuity",
      "The hard parts of software engineering are often outside the diff.",
      colors.red,
    ),
    splitColumns(
      openList("They can produce", ["plausible code", "useful analysis", "rapid first drafts"], colors.red),
      openList("They often lose", ["intent", "repo context", "invariants", "proof obligations", "handoff state"], colors.red),
    ),
    footer("Core claim: the failure is not code generation; it is continuity around the generated work."),
  ],
  "why",
);

// 3. Consultants
addSlide(
  presentation,
  [
    header("Mental model", "AI coding agents are consultants", "Temporary contributors need onboarding, boundaries, review expectations, and handoff.", colors.amber),
    grid(
      {
        name: "consultant-grid",
        width: fill,
        height: fill,
        columns: [auto, auto, auto],
        rows: [fr(1)],
        columnGap: 42,
      },
      [
        openList("Consultant problem", ["onboarding cost", "knowledge-transfer gaps", "local conventions missed", "handoff quality varies"], colors.amber, 610, 25),
        text("→", {
          name: "consultant-arrow",
          width: fixed(90),
          height: hug,
          style: { fontFace: font, fontSize: 64, bold: true, color: colors.amber, alignment: "center" },
        }),
        openList("AW response", ["startup routing", "Memory", "Planning", "ownership ledgers", "proof routing"], colors.teal, 610, 25),
      ],
    ),
    footer("The agent can do real work; the repo needs an operating structure that makes temporary work cumulative."),
  ],
  "consultants",
);

// 4. What
addSlide(
  presentation,
  [
    header("What", "Move agent operating context into the repo", "Agent platforms optimize the current session. AW optimizes durable repository context.", colors.teal),
    bigQuote(
      "Agent platforms help an agent work. AW helps the repo remember, route, bound, prove, and continue that work.",
      "The goal is synergy: keep native agent capabilities, but promote durable decisions into shared repo state.",
      colors.teal,
    ),
  ],
  "what",
);

// 5. How loop
addSlide(
  presentation,
  [
    header("How", "Make the correct operating path cheaper than guessing", "A small loop turns chat-local work into repo-visible continuity.", colors.blue),
    row(
      { name: "loop-row", width: fill, height: fill, gap: 25 },
      [
        arrowStep("start", "thin adapter + compact context", colors.blue),
        arrowStep("route", "config, Memory, Planning, proof", colors.teal),
        arrowStep("work", "bounded scope and ownership", colors.purple),
        arrowStep("prove", "changed-path validation", colors.amber),
        arrowStep("close", "intent, proof, residue, next owner", colors.red),
      ],
    ),
    footer("This is steering by context, constraints, proof, and continuation; not scripting every action."),
  ],
  "loop",
);

// 6. Adaptive assurance
addSlide(
  presentation,
  [
    header(
      "How",
      "Assurance should scale with risk",
      "AW routes agents toward the smallest credible proof, then raises the burden when scope or blast radius grows.",
      colors.amber,
    ),
    grid(
      {
        name: "assurance-grid",
        width: fill,
        height: fill,
        columns: [auto, auto, auto],
        rows: [fr(1)],
        columnGap: 44,
      },
      [
        openList("Low risk", ["local edit", "known owner", "clear intent", "cheap proof"], colors.teal, 520, 25),
        text("→", {
          name: "assurance-arrow",
          width: fixed(90),
          height: hug,
          style: { fontFace: font, fontSize: 64, bold: true, color: colors.amber, alignment: "center" },
        }),
        openList("Raise assurance", ["cross-boundary work", "unclear ownership", "migration or policy risk", "larger proof surface"], colors.amber, 720, 25),
      ],
    ),
    footer("The control model is adaptive: avoid ritual for trivial work, but make risk visible before it becomes rework."),
  ],
  "assurance",
);

// 7. Three surfaces
addSlide(
  presentation,
  [
    header("Architecture", "Three primary surfaces do most of the work", "Workspace routes. Memory preserves durable knowledge. Planning preserves active execution state.", colors.teal),
    grid(
      { name: "three-surfaces", width: fill, height: fill, columns: [auto, auto, auto], rows: [fr(1)], columnGap: 40 },
      [
        openList("Workspace", ["startup", "config", "lifecycle", "ownership", "proof"], colors.blue, 500, 24),
        openList("Memory", ["invariants", "traps", "runbooks", "anti-rediscovery", "promotion pressure"], colors.teal, 500, 24),
        openList("Planning", ["active state", "execplans", "handoff", "proof expectations", "closeout"], colors.purple, 500, 24),
      ],
    ),
  ],
  "surfaces",
);

// 8. Intent
addSlide(
  presentation,
  [
    header("Distinctive idea", "The prompt is not the whole intent", "AW preserves intent at multiple levels so agents do not collapse product-shaped outcomes into task-shaped slices.", colors.purple),
    grid(
      { name: "intent-levels", width: fill, height: fill, columns: [auto, auto], rows: [fr(1)], columnGap: 70 },
      [
        bullets(["system / product intent", "repo policy intent", "work / lane intent", "execution intent", "closeout intent"], 29, colors.ink, 610),
        bigQuote(
          "The agent completed a task-shaped slice, but the human asked for a product-shaped outcome.",
          "Planning should close slices honestly without silently closing the larger intent.",
          colors.purple,
          820,
          39,
          24,
        ),
      ],
    ),
  ],
  "intent",
);

// 9. Friction
addSlide(
  presentation,
  [
    header("Distinctive idea", "Friction is signal", "A Memory note, hard plan, or repeated steering correction can reveal that the repo itself is too hard to operate.", colors.amber),
    grid(
      { name: "friction-grid", width: fill, height: fill, columns: [auto, auto, auto], rows: [fr(1)], columnGap: 42 },
      [
        openList("Bad loop", ["agent struggles", "add another instruction", "future agents read more noise"], colors.red, 610, 25),
        text("→", {
          name: "friction-arrow",
          width: fixed(85),
          height: hug,
          style: { fontFace: font, fontSize: 64, bold: true, color: colors.amber, alignment: "center" },
        }),
        openList("Better loop", ["capture the lesson", "promote to the right surface", "fix the underlying affordance"], colors.teal, 650, 25),
      ],
    ),
    footer("Memory and Planning are not only compensation; they create improvement pressure."),
  ],
  "friction",
);

// 10. Weak/strong
addSlide(
  presentation,
  [
    header("Operating economics", "Weak agents get safer; strong agents get cheaper", "AW reduces the amount of repo reasoning that each agent must reconstruct from scratch.", colors.blue),
    splitColumns(
      openList("Weak agents", ["too much implicit context", "guess the edit surface", "run convenient proof", "lose the handoff"], colors.red),
      openList("Strong agents", ["can reconstruct context", "but pay in tokens, time, and review", "AW frees reasoning for the actual engineering problem"], colors.blue),
      [fr(1), fr(1.1)],
    ),
    footer("Make implicit context explicit, checked-in, and queryable."),
  ],
  "economics",
);

// 11. Cost model
addSlide(
  presentation,
  [
    header("Cost model", "The expensive failure is rework", "AI can make the first pass look cheap while moving cost into review, repair, and later rediscovery.", colors.red),
    row(
      { name: "rework-chain", width: fill, height: grow(1), gap: 24 },
      [
        arrowStep("wrong context", "the system is misunderstood", colors.red),
        arrowStep("wrong implementation", "locally plausible", colors.red),
        arrowStep("weak proof", "confidence without coverage", colors.amber),
        arrowStep("late discovery", "future work depends on it", colors.purple),
        arrowStep("redo", "pay the real cost", colors.ink),
      ],
    ),
    bigQuote(
      "AW spends a little effort upfront so teams spend less effort later re-understanding, repairing, and redoing agent-assisted work.",
      "The overhead should earn its place by reducing total successful-completion cost.",
      colors.red,
    ),
  ],
  "cost",
);

// 12. What it is not
addSlide(
  presentation,
  [
    header("Boundary", "What Agentic Workspace is not", "The package targets durable intent, context, proof, ownership, and handoff state. It should not absorb mature engineering controls.", colors.muted),
    grid(
      { name: "not-grid", width: fill, height: fill, columns: [auto, auto], rows: [fr(1)], columnGap: 80 },
      [
        bullets(["not Jira", "not CI", "not RAG memory", "not autonomous orchestration", "not a replacement for review"], 29, colors.ink, 700),
        bullets(["not security governance", "not dependency/licensing tooling", "not human accountability", "not a general plugin platform today"], 29, colors.ink, 740),
      ],
    ),
  ],
  "not",
);

// 13. Close
addSlide(
  presentation,
  [
    header("Takeaway", "Repo state beats chat state", "If agent work must survive tools, sessions, branches, and handoffs, the operating context belongs in the repository.", colors.teal),
    bigQuote(
      "The goal is not more generated code. The goal is lower cost to continue, review, and trust agent-assisted work.",
      "Agentic Workspace is a small repo-native layer for making that work cumulative.",
      colors.teal,
    ),
    footer("Suggested demo: fresh agent enters repo -> start/preflight -> summary -> proof -> closeout."),
  ],
  "close",
);

await PresentationFile.exportPptx(presentation).then((blob) => blob.save(OUT));

const slideCount = presentation.slides.count;
for (let i = 0; i < slideCount; i += 1) {
  const slide = presentation.slides.getItem(i);
  const png = await presentation.export({ slide, format: "png" });
  await saveBlob(png, `${SCRATCH}/slide-${String(i + 1).padStart(2, "0")}.png`);
  const layout = await presentation.export({ slide, format: "layout" });
  await saveBlob(layout, `${SCRATCH}/slide-${String(i + 1).padStart(2, "0")}.layout.json`);
}

console.log(JSON.stringify({ ok: true, slides: slideCount, output: OUT }, null, 2));
