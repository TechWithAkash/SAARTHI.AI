"use client";

import React from "react";

interface Node {
  id: string;
  label: string;
  x: number;
  y: number;
}

interface Edge {
  source: string;
  target: string;
}

const NODES: Node[] = [
  { id: "steps",         label: "Activity",     x: 80,  y: 60 },
  { id: "stress_level",  label: "Stress",       x: 80,  y: 240 },
  { id: "sleep",         label: "Sleep",        x: 220, y: 150 },
  { id: "diet_score",    label: "Diet",         x: 360, y: 60 },
  { id: "bmi",           label: "BMI",          x: 420, y: 180 },
  { id: "heart_rate",    label: "Heart Rate",   x: 520, y: 240 },
  { id: "risk_score",    label: "HEALTH RISK",  x: 640, y: 150 },
];

const EDGES: Edge[] = [
  { source: "stress_level", target: "heart_rate" },
  { source: "stress_level", target: "sleep" },
  { source: "stress_level", target: "risk_score" },
  { source: "sleep",        target: "heart_rate" },
  { source: "sleep",        target: "diet_score" },
  { source: "sleep",        target: "risk_score" },
  { source: "diet_score",   target: "bmi" },
  { source: "diet_score",   target: "risk_score" },
  { source: "bmi",          target: "heart_rate" },
  { source: "bmi",          target: "risk_score" },
  { source: "steps",        target: "bmi" },
  { source: "steps",        target: "sleep" },
  { source: "steps",        target: "risk_score" },
  { source: "heart_rate",   target: "risk_score" },
];

interface Props {
  primaryCause?: string;
  causalChain?: string;
}

export default function CausalMap({ primaryCause, causalChain }: Props) {
  const chainNodes = causalChain
    ? causalChain.split(" → ").flatMap((seg) => seg.split(" & "))
    : [];
  

  const isEdgeInChain = (source: string, target: string) => {
    if (primaryCause && source === primaryCause) return true;
    if (!causalChain) return false;
    return chainNodes.includes(source) && chainNodes.includes(target);
  };

  // All nodes directly targeted by the primary cause
  const directTargets = new Set(
    primaryCause
      ? EDGES.filter(e => e.source === primaryCause).map(e => e.target)
      : []
  );

  const getNodeColor = (id: string) => {
    if (id === primaryCause) return "#22C55E";           // vivid green — root cause
    if (directTargets.has(id)) return "#FDE68A";        // amber tint — direct mediator
    if (chainNodes.includes(id)) return "#BBF7D0";      // light green — chain node
    return "#F3F4F6";                                   // grey — inactive
  };

  const getNodeStroke = (id: string) => {
    if (id === primaryCause) return "#16A34A";
    if (directTargets.has(id)) return "#F59E0B";
    if (chainNodes.includes(id)) return "#22C55E";
    return "#E5E7EB";
  };

  const getTextFill = (id: string) => {
    if (id === primaryCause || directTargets.has(id) || chainNodes.includes(id)) return "#111827";
    return "#9CA3AF";
  };

  return (
    <div className="w-full bg-white rounded-2xl border border-slate-200 p-6 shadow-xs overflow-hidden">
      <div className="flex justify-between items-center mb-6">
        <div>
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Directed Acyclic Graph</span>
          <h3 className="text-base font-bold text-slate-900">Causal Relationship Matrix</h3>
        </div>
        <div className="flex gap-4">
          <LegendItem color="#22C55E" label="Root Cause" />
          <LegendItem color="#F59E0B" label="Mediator Node" />
        </div>
      </div>

      <div className="relative aspect-[720/300] w-full">
        <svg viewBox="0 0 720 300" className="w-full h-full preserve-3d">
          <style dangerouslySetInnerHTML={{__html: `
            @keyframes dataFlow {
              to { stroke-dashoffset: -20; }
            }
            .path-flow {
              stroke-dasharray: 6 6;
              animation: dataFlow 0.8s linear infinite;
            }
          `}} />
          {/* Defs for arrows */}
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#D1D5DB" />
            </marker>
            <marker id="arrow-active" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#F59E0B" />
            </marker>
          </defs>

          {/* Edges */}
          {EDGES.map((edge) => {
            const s = NODES.find(n => n.id === edge.source)!;
            const t = NODES.find(n => n.id === edge.target)!;
            const active = isEdgeInChain(edge.source, edge.target);

            return (
              <line
                key={`${edge.source}-${edge.target}`}
                x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                stroke={active ? "#F59E0B" : "#D1D5DB"}
                strokeWidth={active ? 2.5 : 1.5}
                strokeDasharray={active ? "6 4" : undefined}
                markerEnd={`url(#${active ? "arrow-active" : "arrow"})`}
                style={active ? { animation: "dataFlow 0.8s linear infinite" } : undefined}
              />
            );
          })}

          {/* Nodes */}
          {NODES.map((node) => {
            const isActive = chainNodes.includes(node.id) || directTargets.has(node.id);
            const isPrimary = node.id === primaryCause;

            return (
              <g key={node.id} className="cursor-default select-none">
                {/* Glow ring */}
                {(isActive || isPrimary) && (
                  <circle
                    cx={node.x} cy={node.y} r={30}
                    fill={isPrimary ? "#22C55E" : "#F59E0B"}
                    fillOpacity={0.15}
                  />
                )}

                {/* Main node circle */}
                <circle
                  cx={node.x} cy={node.y} r={24}
                  fill={getNodeColor(node.id)}
                  stroke={getNodeStroke(node.id)}
                  strokeWidth={isPrimary || isActive ? 2 : 1}
                />

                {/* Label */}
                <text
                  x={node.x} y={node.y + 42}
                  textAnchor="middle"
                  fontSize="9"
                  fontWeight="700"
                  letterSpacing="0.08em"
                  fill={getTextFill(node.id)}
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div style={{ backgroundColor: color }} className="w-2 h-2 rounded-full" />
      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{label}</span>
    </div>
  );
}
