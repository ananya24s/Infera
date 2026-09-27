import { useEffect, useRef } from "react";
import cytoscape, { type ElementDefinition } from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import type { KnowledgeGraph } from "../types/api";

cytoscape.use(coseBilkent);

const EDGE_COLOR: Record<string, string> = {
  supports: "#2f9e44",
  contradicts: "#e03131",
  cites: "#868e96",
  extracted_from: "#adb5bd",
};

// Light text with a dark outline so labels stay readable wherever they land —
// over a node or over the dark page behind it.
const LABEL_TEXT = {
  color: "#e6f5ec",
  "text-outline-color": "#0a0b0d",
  "text-outline-width": 2,
  "text-wrap": "wrap",
} as const;

export default function KnowledgeGraphView({ graph }: { graph: KnowledgeGraph }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const elements: ElementDefinition[] = [
      ...graph.nodes.map((n) => ({
        data: { id: n.id, label: n.label.slice(0, 60), type: n.type },
      })),
      ...graph.edges.map((e) => ({
        data: { id: e.id, source: e.source, target: e.target, type: e.type },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      minZoom: 0.3,
      maxZoom: 2.5,
      style: [
        {
          selector: 'node[type = "paper"]',
          style: { "background-color": "#4263eb", width: 22, height: 22, "font-size": 10, "text-max-width": "120px", ...LABEL_TEXT },
        },
        {
          selector: 'node[type = "claim"]',
          style: {
            "background-color": "#f08c00",
            shape: "round-rectangle",
            width: 14,
            height: 14,
            "font-size": 10,
            "text-max-width": "140px",
            ...LABEL_TEXT,
          },
        },
        {
          // Only hypotheses are labeled by default — a result has a handful of
          // them but dozens of papers and claims, and labeling all of those is
          // what made the graph read as a wall of text. Paper and claim text
          // shows on hover instead.
          selector: 'node[type = "hypothesis"]',
          style: {
            "background-color": "#39d98a",
            shape: "diamond",
            label: "data(label)",
            "font-size": 12,
            "font-weight": 700,
            width: 34,
            height: 34,
            "text-max-width": "140px",
            "text-valign": "bottom",
            "text-margin-y": 6,
            ...LABEL_TEXT,
          },
        },
        {
          selector: "node.hover",
          style: { label: "data(label)", "z-index": 10 },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": (ele) => EDGE_COLOR[ele.data("type")] ?? "#ccc",
            "target-arrow-color": (ele) => EDGE_COLOR[ele.data("type")] ?? "#ccc",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.75,
          },
        },
        {
          selector: 'edge[type = "cites"]',
          style: { "line-style": "dashed", opacity: 0.5 },
        },
        {
          selector: 'edge[type = "extracted_from"]',
          style: { "target-arrow-shape": "none", opacity: 0.35 },
        },
      ],
      // cose-bilkent tiles disconnected groups into a grid by default, which is
      // what turned results with off-topic papers into rows of identical
      // stars. With tiling off and stronger gravity, loose groups settle
      // around the connected core instead.
      layout: {
        name: "cose-bilkent",
        animate: false,
        tile: false,
        gravity: 0.8,
        gravityRange: 1.5,
      } as cytoscape.LayoutOptions,
    });

    cy.on("mouseover", "node", (e) => e.target.addClass("hover"));
    cy.on("mouseout", "node", (e) => e.target.removeClass("hover"));
    cy.on("tap", "node", (e) => e.target.toggleClass("hover"));

    return () => cy.destroy();
  }, [graph]);

  return (
    <div className="panel kg-panel">
      <h2>Knowledge Graph</h2>
      <div className="kg-legend">
        <span><i className="dot paper" /> paper</span>
        <span><i className="dot claim" /> claim</span>
        <span><i className="dot hypothesis" /> hypothesis</span>
        <span><i className="line supports" /> supports</span>
        <span><i className="line contradicts" /> contradicts</span>
        <span><i className="line cites" /> cites</span>
        <span className="kg-hint">hover a node for its text</span>
      </div>
      <div ref={containerRef} className="kg-canvas" />
    </div>
  );
}
