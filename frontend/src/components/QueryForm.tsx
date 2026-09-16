import { useState } from "react";

interface Props {
  onSubmit: (question: string) => void;
  loading: boolean;
}

export default function QueryForm({ onSubmit, loading }: Props) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && !loading) onSubmit(question.trim());
  };

  return (
    <form className="query-form" onSubmit={handleSubmit}>
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a research question, e.g. Does creatine supplementation improve cognitive performance?"
        disabled={loading}
      />
      <button type="submit" disabled={loading || !question.trim()}>
        {loading ? "Researching…" : "Research"}
      </button>
    </form>
  );
}
