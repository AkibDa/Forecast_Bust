import React from 'react';
import { TrendingUp, AlertCircle } from 'lucide-react';

export const ConfidenceTrendCard = ({
  timeseriesData,
  loading,
  error,
  currentLeadDay,
  onSelectLeadDay,
}) => {
  if (loading) {
    return (
      <div className="panel-card bg-slate-900/90 border border-slate-700/80 p-3.5 rounded-lg shadow-md animate-pulse">
        <div className="h-4 bg-slate-800 rounded w-1/2 mb-3" />
        <div className="h-28 bg-slate-950 rounded border border-slate-800" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-card bg-slate-900/90 border border-slate-700/80 p-3.5 rounded-lg shadow-md">
        <div className="flex items-center gap-1.5 text-xs font-mono text-slate-300 font-semibold mb-2">
          <TrendingUp size={14} className="text-cyan-400" />
          <span>10-DAY CONFIDENCE TRAJECTORY</span>
        </div>
        <p className="text-xs text-rose-400 font-mono bg-rose-500/10 p-2 rounded border border-rose-500/20">
          {error}
        </p>
      </div>
    );
  }

  const leadTimes = timeseriesData?.lead_times || [];
  const isSingleDay = leadTimes.length === 1;

  return (
    <div className="confidence-trend-card panel-card bg-slate-900/90 border border-slate-700/80 p-3.5 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs font-mono text-slate-200 font-semibold">
          <TrendingUp size={14} className="text-cyan-400" />
          <span>10-DAY CONFIDENCE TRAJECTORY</span>
        </div>
        <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
          {leadTimes.length} {leadTimes.length === 1 ? 'HORIZON' : 'HORIZONS'}
        </span>
      </div>

      {leadTimes.length === 0 ? (
        <div className="text-xs font-mono text-slate-500 italic p-4 text-center bg-slate-950/60 rounded border border-slate-800">
          No trajectory data returned for this cell.
        </div>
      ) : isSingleDay ? (
        <div className="space-y-2">
          <div className="bg-slate-950 p-3 rounded border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-mono text-cyan-400 font-semibold">
                DAY {leadTimes[0].lead_day} (+24h)
              </div>
              <div className="text-sm font-bold font-mono text-slate-200">
                Confidence: {(leadTimes[0].confidence_score * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] font-mono text-rose-400 font-semibold">
                BUST PROBABILITY
              </div>
              <div className="text-sm font-bold font-mono text-rose-300">
                {(leadTimes[0].bust_probability * 100).toFixed(2)}%
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1.5 p-2 bg-amber-500/10 border border-amber-500/20 rounded text-[10px] font-mono text-amber-300">
            <AlertCircle size={13} className="shrink-0" />
            <span>
              Live GFS cycle currently stores Day 1 (f024) only. Extended 10-day trajectories are active on historical archive dates.
            </span>
          </div>
        </div>
      ) : (
        /* Multi-day interactive SVG bar/trajectory chart */
        <div className="space-y-2">
          <div className="h-28 w-full bg-slate-950/80 rounded border border-slate-800 p-2 flex items-end justify-between gap-1.5 relative">
            {leadTimes.map((lt) => {
              const confPct = lt.confidence_score * 100;
              const isCurrent = lt.lead_day === currentLeadDay;

              // Color based on confidence
              let barBg = 'bg-cyan-500/80';
              if (confPct < 90) barBg = 'bg-amber-500/80';
              if (confPct < 75) barBg = 'bg-rose-500/80';

              return (
                <div
                  key={`traj-${lt.lead_day}`}
                  onClick={() => onSelectLeadDay && onSelectLeadDay(lt.lead_day)}
                  className={`flex-1 flex flex-col items-center justify-end h-full cursor-pointer group relative transition-transform ${
                    isCurrent ? 'scale-105' : 'hover:scale-102 opacity-80 hover:opacity-100'
                  }`}
                >
                  {/* Tooltip on hover */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover:block z-50 w-28 p-1.5 bg-slate-900 border border-slate-700 text-[10px] font-mono text-slate-100 rounded shadow-2xl pointer-events-none text-center">
                    <div className="font-bold text-cyan-400">Day {lt.lead_day} (+{lt.lead_day * 24}h)</div>
                    <div>Conf: {confPct.toFixed(1)}%</div>
                    <div className="text-rose-400">Bust: {(lt.bust_probability * 100).toFixed(2)}%</div>
                  </div>

                  {/* Bar */}
                  <div
                    className={`w-full rounded-t transition-all ${barBg} ${
                      isCurrent ? 'ring-1 ring-white shadow-[0_0_8px_rgba(6,182,212,0.6)]' : ''
                    }`}
                    style={{ height: `${Math.max(15, confPct * 0.85)}%` }}
                  />

                  {/* Day Label */}
                  <span
                    className={`text-[9px] font-mono mt-1 ${
                      isCurrent ? 'text-cyan-300 font-bold underline' : 'text-slate-500'
                    }`}
                  >
                    D{lt.lead_day}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 pt-0.5">
            <span>D1 (+24h)</span>
            <span className="text-slate-500">Click bar to inspect Day horizon</span>
            <span>D{leadTimes[leadTimes.length - 1].lead_day} (+{leadTimes[leadTimes.length - 1].lead_day * 24}h)</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConfidenceTrendCard;
