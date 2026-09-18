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
      style: [
        {
          selector: 'node[type = "paper"]',
          style: {
            "background-color": "#4263eb",
            label: "data(label)",
            "font-size": 7,
            width: 22,
            height: 22,
            color: "#1a1a1a",
            "text-wrap": "wrap",
            "text-max-width": "80px",
          },
        },
        {
          selector: 'node[type = "claim"]',
          style: {
            "background-color": "#f08c00",
            shape: "round-rectangle",
            label: "data(label)",
            "font-size": 6,
            width: 14,
            height: 14,
            color: "#1a1a1a",
            "text-wrap": "wrap",
            "text-max-width": "70px",
          },
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
      layout: { name: "cose-bilkent", animate: false } as cytoscape.LayoutOptions,
    });

    return () => cy.destroy();
  }, [graph]);

  return (
    <div className="panel kg-panel">
      <h2>Knowledge Graph</h2>
      <div className="kg-legend">
        <span><i className="dot paper" /> paper</span>
        <span><i className="dot claim" /> claim</span>
        <span><i className="line supports" /> supports</span>
        <span><i className="line contradicts" /> contradicts</span>
        <span><i className="line cites" /> cites</span>
      </div>
      <div ref={containerRef} className="kg-canvas" />
    </div>
  );
}
