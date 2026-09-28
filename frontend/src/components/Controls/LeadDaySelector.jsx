import React from 'react';
import { Clock } from 'lucide-react';

export const LeadDaySelector = ({
  currentLeadDay,
  supportedLeadDays = [1],
  onSelectLeadDay,
  isLiveMode,
}) => {
  const leadDays = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  return (
    <div className="lead-day-selector flex flex-wrap items-center gap-2 sm:gap-3 px-4 py-2 bg-slate-900/40 border-b border-slate-800/60">
      <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400">
        <Clock size={14} className="text-cyan-400" />
        <span className="font-semibold text-slate-200">LEAD TIME:</span>
      </div>

      {/* Button Group D1 - D10 */}
      <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 shadow-inner overflow-x-auto max-w-full">
        {leadDays.map((day) => {
          const isSupported = supportedLeadDays.includes(day);
          const isSelected = currentLeadDay === day;

          return (
            <div key={`lead-${day}`} className="relative group">
              <button
                type="button"
                onClick={() => isSupported && onSelectLeadDay(day)}
                disabled={!isSupported}
                className={`px-2.5 sm:px-3 py-1 rounded text-xs font-mono font-medium transition-all duration-150 cursor-pointer ${
                  isSelected
                    ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-[0_0_12px_rgba(6,182,212,0.4)] border border-cyan-400 font-bold'
                    : isSupported
                    ? 'text-slate-300 hover:text-cyan-300 hover:bg-slate-800/80 border border-transparent'
                    : 'text-slate-600 opacity-40 cursor-not-allowed border border-transparent'
                }`}
                title={
                  !isSupported
                    ? 'Extended lead unavailable for current live GFS data.'
                    : `Forecast issued for +${day * 24}h (Day ${day})`
                }
              >
                D{day}
              </button>

              {/* Tooltip on disabled hover */}
              {!isSupported && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50 w-44 p-1.5 bg-slate-900 border border-slate-700 text-[10px] font-mono text-amber-300 rounded shadow-xl pointer-events-none text-center">
                  Extended lead unavailable for current live GFS data.
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="text-[11px] font-mono text-slate-400 ml-1">
        <span className="text-cyan-400 font-bold">+{currentLeadDay * 24}h</span> Valid Horizon
        {isLiveMode && supportedLeadDays.length === 1 && (
          <span className="ml-2 text-slate-500 italic hidden md:inline">
            (GFS f024 single-cycle operational run)
          </span>
        )}
      </div>
    </div>
  );
};

export default LeadDaySelector;
