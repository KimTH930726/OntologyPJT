import { useEffect, useRef } from "react";
import { DataSet } from "vis-data";
import { Network } from "vis-network";
import type { GraphNode, GraphRelationship } from "@/api/types";

const typeColors: Record<string, string> = {
  Policy: "#3b82f6",
  Order: "#10b981",
  OrderItem: "#34d399",
  Payment: "#f59e0b",
  Refund: "#ef4444",
  Delivery: "#8b5cf6",
  Product: "#06b6d4",
  Condition: "#eab308",
  DocumentChunk: "#94a3b8",
};

export default function GraphCanvas({
  nodes,
  relationships,
  height = 520,
  onNodeClick,
}: {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
}) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (!elRef.current) return;

    const visNodes = new DataSet(
      nodes.map((n) => ({
        id: n.normalized_name,
        label: n.name || n.normalized_name,
        color: { background: typeColors[n.type] || "#cbd5e1", border: "#1e293b" },
        font: { color: "#ffffff" },
        title: `${n.type} · ${n.normalized_name}`,
      })),
    );

    const visEdges = new DataSet(
      relationships.map((r, idx) => ({
        id: r.id || `e_${idx}`,
        from: r.source,
        to: r.target,
        label: r.relation,
        arrows: "to",
        font: { align: "middle", size: 10, color: "#475569" },
        color: { color: "#94a3b8" },
        smooth: { enabled: true, type: "dynamic", roundness: 0.4 },
      })),
    );

    const network = new Network(
      elRef.current,
      { nodes: visNodes, edges: visEdges },
      {
        autoResize: true,
        layout: { improvedLayout: true },
        physics: {
          enabled: true,
          stabilization: { iterations: 80 },
          barnesHut: { springLength: 140 },
        },
        interaction: { hover: true, navigationButtons: true },
        nodes: {
          shape: "dot",
          size: 18,
          borderWidth: 2,
        },
      },
    );

    networkRef.current = network;
    if (onNodeClick) {
      network.on("selectNode", (params) => {
        const id = params.nodes?.[0] as string | undefined;
        if (!id) return;
        const node = nodes.find((n) => n.normalized_name === id);
        if (node) onNodeClick(node);
      });
    }

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [nodes, relationships, onNodeClick]);

  return (
    <div
      ref={elRef}
      style={{ height }}
      className="rounded-md border border-slate-200 bg-white"
    />
  );
}
