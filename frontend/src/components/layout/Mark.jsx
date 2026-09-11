/**
 * Mark
 * The brand mark: a simple rounded-square badge with an open-book glyph.
 * Flat and single-color by design — no stamp/dashed-line ornamentation —
 * so it reads clean at any size, from a 20px favicon to a 56px hero mark.
 */
export default function Mark({ size = 32, tone = "moss" }) {
  const bg = tone === "paper" ? "var(--color-surface)" : "var(--color-moss)";
  const fg = tone === "paper" ? "var(--color-moss)" : "var(--color-paper-100)";
  const radius = size * 0.28;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className="flex-shrink-0"
      aria-hidden="true"
    >
      <rect width="32" height="32" rx={radius} fill={bg} />
      <path
        d="M16 11.2c-1.3-1.1-3-1.7-5-1.7-.4 0-.7.3-.7.7v9.4c0 .4.3.7.7.7 2 0 3.7.6 5 1.7 1.3-1.1 3-1.7 5-1.7.4 0 .7-.3.7-.7v-9.4c0-.4-.3-.7-.7-.7-2 0-3.7.6-5 1.7Z"
        stroke={fg}
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M16 11.2v10.8" stroke={fg} strokeWidth="1.4" />
    </svg>
  );
}
