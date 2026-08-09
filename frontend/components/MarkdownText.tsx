"use client";

import React from "react";

// The chat system prompt tells the model to "use markdown for structure —
// bold, bullet points" (backend/services/chat_service.py). The /chat page
// already has its own renderer for this; AuraChat (the floating widget,
// mounted globally in layout.tsx) never got the equivalent and was printing
// "**bold**" / "* item" literally. Shared here so both stay consistent
// instead of drifting into two different ad-hoc implementations.
export function MarkdownText({ text, streaming }: { text: string; streaming?: boolean }) {
  if (!text) return null;
  const lines = text.split("\n");
  return (
    <div className="space-y-1.5">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />;
        if (line.trim().startsWith("• ") || line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
          return (
            <div key={i} className="flex items-start gap-2">
              <span className="w-1 h-1 bg-current opacity-40 rounded-full shrink-0 mt-2" />
              <span>{renderInline(line.replace(/^[•\-*]\s*/, ""))}</span>
            </div>
          );
        }
        if (line.trim().startsWith("_") && line.trim().endsWith("_") && line.trim().length > 2) {
          return <p key={i} className="text-xs opacity-70 italic">{line.trim().slice(1, -1)}</p>;
        }
        return <p key={i}>{renderInline(line)}</p>;
      })}
      {streaming && (
        <span className="inline-block w-1.5 h-4 bg-current opacity-50 rounded-sm animate-pulse ml-0.5 align-middle" />
      )}
    </div>
  );
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-bold">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
