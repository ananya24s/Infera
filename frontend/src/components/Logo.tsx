/** Infera's mark: the same diamond used for a "hypothesis" node in the
 * knowledge graph, with a checkmark — literally "a claim, checked." Reused
 * as the header icon and (rendered to public/favicon.svg) the browser favicon. */
export default function Logo({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path
        d="M16 2 L30 16 L16 30 L2 16 Z"
        fill="#132a20"
        stroke="#39d98a"
        strokeWidth="2"
      />
      <path
        d="M10 16.5 L14 20.5 L22 11.5"
        stroke="#39d98a"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
