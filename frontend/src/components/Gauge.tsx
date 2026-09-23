"use client";

import React from "react";

interface GaugeProps {
  /** Value to plot, in the same unit as min/max (e.g. percent). */
  value: number;
  min?: number;
  max?: number;
  label: string;
  sublabel?: string;
}

/**
 * Half-donut gauge, three fixed zones (critical / warning / healthy) with a
 * needle pointing at the current value. Deliberately restrained: pale zone
 * tints, a single dark needle, no neon — see DESIGN.md "The Control Room".
 */
function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 180) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end = polarToCartesian(cx, cy, r, endAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;
}

export default function Gauge({ value, min = -10, max = 40, label, sublabel }: GaugeProps) {
  const clamped = Math.max(min, Math.min(max, value));
  const t = (clamped - min) / (max - min);
  const needleAngle = t * 180;

  const cx = 100;
  const cy = 95;
  const r = 78;

  const needleTip = polarToCartesian(cx, cy, r - 14, needleAngle);

  let zoneColor = "#e11d48"; // signal-critical
  if (value >= min + (max - min) * 0.66) zoneColor = "#059669"; // signal-healthy
  else if (value >= min + (max - min) * 0.33) zoneColor = "#d97706"; // signal-warning

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 115" className="w-full max-w-[220px]">
        <path d={arcPath(cx, cy, r, 0, 60)} stroke="#fecdd3" strokeWidth="14" fill="none" strokeLinecap="round" />
        <path d={arcPath(cx, cy, r, 60, 120)} stroke="#fde68a" strokeWidth="14" fill="none" strokeLinecap="round" />
        <path d={arcPath(cx, cy, r, 120, 180)} stroke="#a7f3d0" strokeWidth="14" fill="none" strokeLinecap="round" />
        <line
          x1={cx}
          y1={cy}
          x2={needleTip.x}
          y2={needleTip.y}
          stroke="#0a0a0a"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r="5" fill="#0a0a0a" />
      </svg>
      <div className="text-center -mt-2">
        <div className="text-2xl font-bold tracking-tight" style={{ color: zoneColor }}>
          {value.toFixed(1)}%
        </div>
        <div className="text-xs font-semibold text-gray-700">{label}</div>
        {sublabel && <div className="text-[11px] text-gray-400 mt-0.5">{sublabel}</div>}
      </div>
    </div>
  );
}
