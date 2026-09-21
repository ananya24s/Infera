import type { ResearchReport } from "../types/api";

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Escape first, then apply formatting — so model/user text can never inject HTML.
function inline(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*(?!\s)(.+?)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

function renderMarkdown(md: string): string {
  const out: string[] = [];
  let listOpen = false;
  const closeList = () => {
    if (listOpen) {
      out.push("</ul>");
      listOpen = false;
    }
  };

  for (const raw of md.split("\n")) {
    const line = raw.trimEnd();
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    if (heading) {
      closeList();
      out.push(`<h3>${inline(heading[2])}</h3>`);
    } else if (bullet) {
      if (!listOpen) {
        out.push("<ul>");
        listOpen = true;
      }
      out.push(`<li>${inline(bullet[1])}</li>`);
    } else if (line.trim() === "") {
      closeList();
    } else {
      closeList();
      out.push(`<p>${inline(line)}</p>`);
    }
  }
  closeList();
  return out.join("\n");
}

export default function ReportView({ report }: { report: ResearchReport }) {
  const isTemplate = report.generated_by === "template";
  return (
    <div className="panel report-panel">
      <h2>
        Report
        <span className={`badge ${isTemplate ? "nei" : "supports"} badge-inline`}>
          {isTemplate ? "template · no LLM" : report.generated_by}
        </span>
        {report.revised && <span className="badge revised">self-checked · {report.revision_notes.length} flagged</span>}
      </h2>
      <div
        className="report-body"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(report.body_markdown) }}
      />
      {report.revision_notes.length > 0 && (
        <details className="revision-notes">
          <summary>Self-check notes ({report.revision_notes.length})</summary>
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
