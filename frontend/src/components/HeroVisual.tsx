/** Fills the empty space beside the headline: an animated illustration of
 * what the product actually does — sources connecting to a hypothesis and
 * resolving to a stance, looping. Pure SVG + CSS, no chart library. */
const NODES = [
  { x: 200, y: 60, stance: "support", delay: 0 },
  { x: 321, y: 130, stance: "support", delay: 0.35 },
  { x: 321, y: 270, stance: "refute", delay: 0.7 },
  { x: 200, y: 340, stance: "support", delay: 1.05 },
  { x: 79, y: 270, stance: "neutral", delay: 1.4 },
  { x: 79, y: 130, stance: "neutral", delay: 1.75 },
] as const;

const CENTER = { x: 200, y: 200 };

export default function HeroVisual() {
  return (
    <div className="hero-visual" aria-hidden="true">
      <svg viewBox="0 0 400 400" className="hero-visual-svg">
        <circle cx={CENTER.x} cy={CENTER.y} r={150} className="hv-ring" />

        {NODES.map((n, i) => {
          const len = Math.hypot(n.x - CENTER.x, n.y - CENTER.y);
          return (
            <line
              key={`e${i}`}
              x1={CENTER.x}
              y1={CENTER.y}
              x2={n.x}
              y2={n.y}
              className={`hv-edge hv-edge-${n.stance}`}
              style={{
                strokeDasharray: len,
                animationDelay: `${n.delay}s`,
                ["--len" as string]: len,
              }}
            />
          );
        })}

        {NODES.map((n, i) => (
          <circle
            key={`n${i}`}
            cx={n.x}
            cy={n.y}
            r={10}
            className={`hv-node hv-node-${n.stance}`}
            style={{ animationDelay: `${n.delay + 0.5}s` }}
          />
        ))}

        <g className="hv-hyp" transform={`translate(${CENTER.x}, ${CENTER.y})`}>
          <path d="M0 -32 L32 0 L0 32 L-32 0 Z" className="hv-hyp-diamond" />
          <path d="M-12 1 L-3 10 L14 -9" className="hv-hyp-check" />
        </g>
      </svg>

      <div className="hero-visual-status">
        <span className="brand-cursor hero-visual-cursor" />
        verifying 6 sources against the hypothesis
      </div>
    </div>
  );
}
