const TEAM = ["Ananya Singh", "Ishika Singh", "Akshat Sharma"];

const LIMITS = [
  "Verification works from abstracts, not full paper text, so it can miss detail that lives in the methods or results sections.",
  "Retrieval covers OpenAlex and arXiv only. Topics outside those sources will have thin evidence.",
  "The verifier is a trained model, not an oracle. Treat verdicts as pointers to evidence, not ground truth.",
  "Nothing here is medical, legal or financial advice.",
];

export default function About() {
  return (
    <div className="page">
      <p className="eyebrow">// about</p>
      <h1 className="page-title">Why Infera exists.</h1>
      <p className="page-lead">
        LLM-written research summaries often cite sources that don&apos;t actually support the claim they&apos;re
        attached to, and there is no easy way to see how strong the evidence is across several sources.
        Infera takes a research question, retrieves real papers, checks each claim against its evidence, and
        produces a report where every claim has been verified, including the report&apos;s own sentences.
      </p>

      <div className="term-block-title">$ whoami --team</div>
      <div className="team-list">
        {TEAM.map((name) => (
          <div className="team-card" key={name}>
            {name}
          </div>
        ))}
      </div>

      <div className="term-block-title">$ cat LIMITS</div>
      <ul className="limits-list">
        {LIMITS.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>

      <div className="term-block-title">$ infera --stack</div>
      <p className="page-lead">
        FastAPI · PyTorch + HuggingFace Transformers · sentence-transformers + FAISS · rank_bm25 · LightGBM ·
        HDBSCAN · React + Cytoscape.js. Data comes live from OpenAlex and arXiv; nothing is fabricated.
      </p>
    </div>
  );
}
