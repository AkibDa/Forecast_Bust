import React, { useState } from 'react';
import { Info, HelpCircle } from 'lucide-react';

export const MapLegend = ({ stats }) => {
  const [showExplanation, setShowExplanation] = useState(false);

  const formatPct = (val) => {
    if (typeof val !== 'number' || isNaN(val)) return '-';
    return (val * 100).toFixed(2) + '%';
  };

  return (
    <div className="map-legend bg-slate-950/85 backdrop-blur-md border border-slate-800/90 rounded-lg p-2.5 text-xs font-mono shadow-2xl text-slate-300 max-w-xs select-none">
      <div className="flex items-center justify-between gap-2 mb-2 pb-1 border-b border-slate-800">
        <span className="text-[11px] font-bold text-slate-200 tracking-wider flex items-center gap-1">
          <span>BUST PROBABILITY (PERCENTILE SCALE)</span>
        </span>
        <button
          onClick={() => setShowExplanation(!showExplanation)}
          className="text-slate-400 hover:text-cyan-300 transition-colors cursor-pointer"
          title="Why percentile scaling?"
        >
          <HelpCircle size={13} />
        </button>
      </div>

      {/* Color Bar */}
      <div className="space-y-1 mb-2">
        <div className="h-2.5 rounded flex overflow-hidden border border-slate-700">
          <div className="flex-1 bg-[#0284c7]" title="Quartile 1 (Lowest risk)" />
          <div className="flex-1 bg-[#06b6d4]" title="Quartile 2" />
          <div className="flex-1 bg-[#eab308]" title="Quartile 3" />
          <div className="flex-1 bg-[#f97316]" title="P75 - P90 (Elevated risk)" />
          <div className="flex-1 bg-[#ef4444]" title="P90 - P95 (High risk)" />
          <div className="flex-1 bg-[#dc2626]" title="P95 - P100 (Critical risk)" />
        </div>
        <div className="flex justify-between text-[10px] text-slate-400 font-mono">
          <span>{stats ? formatPct(stats.min) : 'MIN'} (P0)</span>
          <span>{stats ? formatPct(stats.p50) : 'MED'}</span>
          <span>{stats ? formatPct(stats.max) : 'MAX'} (P100)</span>
        </div>
      </div>

      {/* Legend Items */}
      <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[10px] text-slate-400 pt-1">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#0284c7]" />
          <span>High Confidence (P0-P25)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#eab308]" />
          <span>Moderate Risk (P50-P75)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#06b6d4]" />
          <span>Nominal (P25-P50)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#ef4444]" />
          <span>Elevated Bust (P75-P100)</span>
        </div>
      </div>

      {showExplanation && (
        <div className="mt-2.5 pt-2 border-t border-slate-800 text-[10px] text-slate-400 leading-relaxed bg-slate-900/60 p-2 rounded">
          <div className="flex items-start gap-1 text-cyan-400 font-semibold mb-1">
            <Info size={12} className="shrink-0 mt-0.5" />
            <span>METEOROLOGICAL SCALING</span>
          </div>
          <p>
            Calibrated model probabilities natively cluster within {stats ? `${formatPct(stats.min)} to ${formatPct(stats.max)}` : '0.3%–1.5%'} because extreme forecast busts represent rare synoptic anomalies. Percentile distribution grading reveals fine spatial risk gradients across India.
          </p>
        </div>
      )}
    </div>
  );
};

export default MapLegend;
