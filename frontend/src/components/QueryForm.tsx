interface Props {
  onSubmit: (question: string) => void;
  loading: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function QueryForm({ onSubmit, loading, value, onChange }: Props) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !loading) onSubmit(value.trim());
  };

  return (
    <form className="query-form" onSubmit={handleSubmit}>
      <div className="query-form-inner">
        <svg className="query-icon" width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M21 21l-4.3-4.3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Ask a research question, e.g. Does creatine supplementation improve cognitive performance?"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !value.trim()}>
          {loading ? "Researching…" : "Research"}
        </button>
      </div>
    </form>
  );
}
