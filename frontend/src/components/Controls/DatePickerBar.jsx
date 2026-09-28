import React, { useMemo } from 'react';
import { Calendar, ChevronDown, Sparkles, History } from 'lucide-react';

export const DatePickerBar = ({
  coverage,
  currentDate,
  onDateChange,
  isLiveMode,
}) => {
  // Extract historical dates and live dates
  const { liveDates, historicalDates } = useMemo(() => {
    let live = [];
    let hist = [];

    if (coverage) {
      if (Array.isArray(coverage)) {
        hist = coverage;
      } else {
        live = coverage.live || [];
        hist = coverage.historical || [];
      }
    }

    return { liveDates: live, historicalDates: hist };
  }, [coverage]);

  return (
    <div className="date-picker-bar flex flex-wrap items-center gap-2 sm:gap-3 px-4 py-2 bg-slate-900/60 border-b border-slate-800/60 text-xs font-mono">
      <div className="flex items-center gap-1.5 text-slate-400">
        <Calendar size={14} className="text-cyan-400" />
        <span className="font-semibold text-slate-200">INIT DATE:</span>
      </div>

      {/* Date Select Dropdown / Custom Input */}
      <div className="relative flex items-center">
        <select
          value={currentDate || ''}
          onChange={(e) => onDateChange(e.target.value)}
          className="appearance-none bg-slate-950 text-cyan-300 font-mono text-xs px-3 py-1.5 pr-8 rounded border border-slate-700 hover:border-cyan-500/60 focus:outline-none focus:border-cyan-400 cursor-pointer shadow-inner"
        >
          {liveDates.length > 0 && (
            <optgroup label="Live GFS Operational Cycle">
              {liveDates.map((d) => (
                <option key={`live-${d}`} value={d}>
                  {d} (Live GFS)
                </option>
              ))}
            </optgroup>
          )}

          {historicalDates.length > 0 && (
            <optgroup label="TIGGE Historical Backtest Archive">
              {historicalDates.map((d) => (
                <option key={`hist-${d}`} value={d}>
                  {d} (TIGGE Archive)
                </option>
              ))}
            </optgroup>
          )}

          {/* Fallback if current date isn't in lists yet */}
          {currentDate && !liveDates.includes(currentDate) && !historicalDates.includes(currentDate) && (
            <option value={currentDate}>{currentDate} (Selected)</option>
          )}
        </select>
        <ChevronDown size={14} className="absolute right-2 text-slate-400 pointer-events-none" />
      </div>

      {/* Mode Tag */}
      <div className="flex items-center gap-1">
        {isLiveMode ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-cyan-950/80 text-cyan-300 border border-cyan-800">
            <Sparkles size={11} className="text-cyan-400" />
            LIVE FORECAST (Day 1 Only)
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-indigo-950/80 text-indigo-300 border border-indigo-800">
            <History size={11} className="text-indigo-400" />
            HISTORICAL ARCHIVE (Days 1–10)
          </span>
        )}
      </div>

      {/* Quick Jump Buttons for Demo / Convenience */}
      <div className="hidden lg:flex items-center gap-1.5 ml-auto">
        <span className="text-[11px] text-slate-500">QUICK SELECT:</span>
        {liveDates.length > 0 && (
          <button
            onClick={() => onDateChange(liveDates[0])}
            className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-all cursor-pointer ${
              currentDate === liveDates[0]
                ? 'bg-cyan-950 text-cyan-300 border-cyan-500'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            Latest Live GFS
          </button>
        )}
        {historicalDates.length > 0 && (
          <button
            onClick={() => onDateChange(historicalDates[0])}
            className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-all cursor-pointer ${
              currentDate === historicalDates[0]
                ? 'bg-indigo-950 text-indigo-300 border-indigo-500'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            Archive Sample ({historicalDates[0]})
          </button>
        )}
      </div>
    </div>
  );
};

export default DatePickerBar;
