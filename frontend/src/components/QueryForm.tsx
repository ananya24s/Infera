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
        <span className="prompt-prefix">research@infera:~$</span>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="ask a research question…"
          disabled={loading}
          autoFocus
        />
        <button type="submit" disabled={loading || !value.trim()}>
          {loading ? "running…" : "run ↵"}
        </button>
      </div>
    </form>
  );
}
