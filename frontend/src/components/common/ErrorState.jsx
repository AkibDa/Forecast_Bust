import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export const ErrorState = ({ message, onRetry, compact = false, className = '' }) => {
  if (compact) {
    return (
      <div className={`error-box-compact flex items-center justify-between text-xs p-2 rounded ${className}`}>
        <div className="flex items-center gap-1.5 text-rose-400">
          <AlertTriangle size={14} className="shrink-0" />
          <span className="truncate">{message}</span>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-cyan-400 hover:text-cyan-300 ml-2 underline text-[11px] font-mono shrink-0 cursor-pointer"
          >
            RETRY
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`error-panel p-4 rounded-lg flex flex-col items-center text-center gap-2.5 ${className}`}>
      <div className="w-8 h-8 rounded-full bg-rose-500/10 flex items-center justify-center text-rose-400 border border-rose-500/20">
        <AlertTriangle size={18} />
      </div>
      <div className="text-xs font-mono uppercase tracking-wider text-rose-400 font-semibold">
        Operational Warning
      </div>
      <p className="text-xs text-slate-300 max-w-xs">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-mono rounded border border-slate-700 flex items-center gap-1.5 cursor-pointer transition-colors"
        >
          <RefreshCw size={12} />
          RETRY REQUEST
        </button>
      )}
    </div>
  );
};

export default ErrorState;
