import type { ResearchReport } from "../types/api";

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderMarkdown(md: string): string {
  return md
    .split("\n")
    .map((line) => {
      if (line.startsWith("## ")) return `<h3>${escapeHtml(line.slice(3))}</h3>`;
      if (line.trim() === "") return "";
      return `<p>${escapeHtml(line)}</p>`;
    })
    .join("\n");
}

export default function ReportView({ report }: { report: ResearchReport }) {
  return (
    <div className="panel report-panel">
      <h2>
        Report
        {report.revised && <span className="badge revised">self-revised</span>}
      </h2>
      <div
        className="report-body"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(report.body_markdown) }}
      />
      {report.revision_notes.length > 0 && (
        <details className="revision-notes">
          <summary>Revision notes ({report.revision_notes.length})</summary>
          <ul>
            {report.revision_notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
