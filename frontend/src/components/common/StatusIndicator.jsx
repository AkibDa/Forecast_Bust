import React from 'react';

export const StatusIndicator = ({ mode = 'live', label, className = '' }) => {
  let dotColor = 'bg-emerald-400';
  let badgeClass = 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10';
  let displayLabel = label || 'OPERATIONAL';

  if (mode === 'live') {
    dotColor = 'bg-cyan-400';
    badgeClass = 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10';
    displayLabel = label || 'LIVE GFS';
  } else if (mode === 'cache') {
    dotColor = 'bg-amber-400';
    badgeClass = 'border-amber-500/30 text-amber-400 bg-amber-500/10';
    displayLabel = label || 'GFS CACHED';
  } else if (mode === 'historical') {
    dotColor = 'bg-indigo-400';
    badgeClass = 'border-indigo-500/30 text-indigo-400 bg-indigo-500/10';
    displayLabel = label || 'TIGGE ARCHIVE';
  } else if (mode === 'climatology_fallback') {
    dotColor = 'bg-orange-400';
    badgeClass = 'border-orange-500/30 text-orange-400 bg-orange-500/10';
    displayLabel = label || 'CLIMATOLOGY';
  } else if (mode === 'offline' || mode === 'failed') {
    dotColor = 'bg-rose-500';
    badgeClass = 'border-rose-500/30 text-rose-400 bg-rose-500/10';
    displayLabel = label || 'OFFLINE';
  }

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium border tracking-wider uppercase ${badgeClass} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} animate-pulse`} />
      <span>{displayLabel}</span>
    </div>
  );
};

export default StatusIndicator;
