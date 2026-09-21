import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AgentTable from "../components/AgentTable";
import QueryForm from "../components/QueryForm";
import SamplePreview from "../components/SamplePreview";
import { useResearch } from "../context/ResearchContext";
import { EXAMPLE_QUESTIONS } from "../lib/examples";

const STEPS = [
  {
    n: "01",
    title: "Retrieve",
    body: "Finds real papers on OpenAlex and arXiv and ranks them with hybrid dense + keyword search. No invented sources.",
  },
  {
    n: "02",
    title: "Verify",
    body: "Every claim is checked against its source by a trained NLI model and labelled supports, refutes, or not enough info.",
  },
  {
    n: "03",
    title: "Report",
    body: "Verdicts become agreement and controversy scores, and the report fact-checks its own sentences before you see it.",
  },
];

export default function Home() {
  const { run, status } = useResearch();
  const navigate = useNavigate();
  const [value, setValue] = useState("");

  const submit = (q: string) => {
    run(q);
    navigate("/research");
  };

  return (
    <div className="page home">
      <section className="home-hero">
        <p className="eyebrow">// evidence checking for research questions</p>
        <h1 className="home-headline">
          Ask a research question.
          <br />
          Every claim gets <span className="hl">checked</span>.
        </h1>
        <p className="home-sub">
          AI-written research summaries often cite sources that don&apos;t actually support the claim, and
          nothing shows you how strong the evidence really is. Infera retrieves real papers, checks each
          claim against its evidence with a trained model, and shows where sources agree and where they
          don&apos;t.
        </p>

        <QueryForm onSubmit={submit} loading={status === "running"} value={value} onChange={setValue} />

        <div className="term-history">
          {EXAMPLE_QUESTIONS.map((q, i) => (
            <button key={q} className="term-history-item" onClick={() => submit(q)}>
              <span className="history-index">{482 + i}</span>
              <span className="history-text">{q}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="term-block-title">$ cat sample_report</div>
        <SamplePreview />
      </section>

      <section className="home-section">
        <div className="term-block-title">$ infera --how</div>
        <div className="steps">
          {STEPS.map((s) => (
            <div className="step-card" key={s.n}>
              <span className="step-n">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="term-block-title">$ ps --agents</div>
        <AgentTable trace={[]} />
      </section>
    </div>
  );
}
