"use client";

import React from "react";

interface SparklineProps {
  values: number[];
  color?: string;
  height?: number;
}

/** Minimal inline trend line for a KPI card. No axes, no labels — the number does the talking. */
export default function Sparkline({ values, color = "#D9720F", height = 28 }: SparklineProps) {
  if (values.length < 2) {
    return <div style={{ height }} />;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 100;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="w-full" style={{ height }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
