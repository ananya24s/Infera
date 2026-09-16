const EXAMPLE_QUESTIONS = [
  "Does creatine supplementation improve cognitive performance?",
  "Is intermittent fasting effective for long-term weight loss?",
  "Do statins reduce cardiovascular risk in healthy adults?",
  "Does screen time before bed impair sleep quality?",
];

const PIPELINE_STAGES = [
  { label: "Query Planning", kind: "llm" },
  { label: "Retrieval", kind: "ml" },
  { label: "Ranking", kind: "ml" },
  { label: "Claim Extraction", kind: "llm" },
  { label: "Verification", kind: "ml" },
  { label: "Stance Clustering", kind: "ml" },
  { label: "Consensus Scoring", kind: "ml" },
  { label: "Graph Builder", kind: "ml" },
  { label: "Report Generation", kind: "llm" },
];

interface Props {
  onExample: (question: string) => void;
}

export default function Hero({ onExample }: Props) {
  return (
    <div className="hero">
      <div className="hero-pipeline" aria-hidden="true">
        {PIPELINE_STAGES.map((stage, i) => (
          <div className="hero-pipeline-item" key={stage.label} style={{ animationDelay: `${i * 90}ms` }}>
            <span className={`hero-node hero-node-${stage.kind}`} />
            <span className="hero-node-label">{stage.label}</span>
            {i < PIPELINE_STAGES.length - 1 && <span className="hero-node-connector" />}
          </div>
        ))}
      </div>

      <div className="hero-examples">
        <span className="hero-examples-label">Try one:</span>
        {EXAMPLE_QUESTIONS.map((q) => (
          <button key={q} className="hero-chip" onClick={() => onExample(q)}>
            {q}
          </button>
        ))}
      </div>

      <div className="hero-legend">
        <span><i className="hero-legend-dot hero-node-ml" /> trained model judgment</span>
        <span><i className="hero-legend-dot hero-node-llm" /> LLM phrasing only</span>
      </div>
    </div>
  );
}
