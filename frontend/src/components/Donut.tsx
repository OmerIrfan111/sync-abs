"use client";

import React from "react";

interface DonutSegment {
  label: string;
  value: number;
  color: string;
}

interface DonutProps {
  segments: DonutSegment[];
  centerLabel: string;
  centerValue: string;
  size?: number;
}

/** Simple real-data donut built from stroke-dasharray arcs. No fabricated proportions — segments always reflect actual counts passed in. */
export default function Donut({ segments, centerLabel, centerValue, size = 140 }: DonutProps) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const strokeWidth = 16;

  let offset = 0;
  const arcs = segments
    .filter((s) => s.value > 0)
    .map((s) => {
      const fraction = total > 0 ? s.value / total : 0;
      const dash = fraction * circumference;
      const arc = (
        <circle
          key={s.label}
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke={s.color}
          strokeWidth={strokeWidth}
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeDashoffset={-offset}
          strokeLinecap="butt"
          transform="rotate(-90 60 60)"
        />
      );
      offset += dash;
      return arc;
    });

  return (
    <div className="flex items-center gap-5">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg viewBox="0 0 120 120" className="w-full h-full">
          <circle cx="60" cy="60" r={radius} fill="none" stroke="#E2E5DE" strokeWidth={strokeWidth} />
          {total > 0 ? arcs : null}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold text-[#1C201B] tracking-tight">{centerValue}</span>
          <span className="text-[10px] text-[#767676] font-medium">{centerLabel}</span>
        </div>
      </div>
      <div className="space-y-2">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-xs">
            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: s.color }} />
            <span className="text-[#767676] font-medium">{s.label}</span>
            <span className="font-bold text-[#1C201B]">{s.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
