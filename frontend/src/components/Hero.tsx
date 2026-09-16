const EXAMPLE_QUESTIONS = [
  "Does creatine supplementation improve cognitive performance?",
  "Is intermittent fasting effective for long-term weight loss?",
  "Do statins reduce cardiovascular risk in healthy adults?",
  "Does screen time before bed impair sleep quality?",
];

const PIPELINE_STAGES = [
  { name: "query_planning", kind: "llm" },
  { name: "retrieval", kind: "model" },
  { name: "ranking", kind: "model" },
  { name: "claim_extraction", kind: "llm" },
  { name: "verification", kind: "model" },
  { name: "stance_clustering", kind: "model" },
  { name: "consensus_scoring", kind: "model" },
  { name: "kg_builder", kind: "model" },
  { name: "report_generation", kind: "llm" },
];

interface Props {
  onExample: (question: string) => void;
}

export default function Hero({ onExample }: Props) {
  return (
    <div className="hero">
      <div className="term-block">
        <div className="term-block-title">
          <span>$ ps --agents</span>
        </div>
        <div className="term-table">
          <div className="term-row term-row-head">
            <span className="col-pid">PID</span>
            <span className="col-name">AGENT</span>
            <span className="col-kind">SOURCE</span>
            <span className="col-state">STATE</span>
          </div>
          {PIPELINE_STAGES.map((stage, i) => (
            <div className="term-row" key={stage.name}>
              <span className="col-pid">{String(i + 1).padStart(2, "0")}</span>
              <span className="col-name">{stage.name}</span>
              <span className={`col-kind kind-${stage.kind}`}>{stage.kind}</span>
              <span className="col-state">
                <i className="state-dot" />
                idle
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="term-block">
        <div className="term-block-title">
          <span>$ history --sample</span>
        </div>
        <div className="term-history">
          {EXAMPLE_QUESTIONS.map((q, i) => (
            <button key={q} className="term-history-item" onClick={() => onExample(q)}>
              <span className="history-index">{482 + i}</span>
              <span className="history-text">{q}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
