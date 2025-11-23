import React from 'react';
import { HEATMAP_DATA } from '../../data/mockData';
import { cn } from '../../utils/cn';

export const Heatmap: React.FC = () => {
    const getColor = (count: number) => {
        if (count === 0) return 'bg-slate-900';
        if (count === 1) return 'bg-emerald-900/40';
        if (count === 2) return 'bg-emerald-700/60';
        if (count === 3) return 'bg-emerald-500/80';
        return 'bg-emerald-400';
    };

    return (
        <div className="w-full overflow-x-auto pb-2">
            <div className="flex gap-1 min-w-max">
                {Array.from({ length: 53 }).map((_, colIndex) => (
                    <div key={colIndex} className="flex flex-col gap-1">
                        {Array.from({ length: 7 }).map((_, rowIndex) => {
                            const dayIndex = colIndex * 7 + rowIndex;
                            const data = HEATMAP_DATA[dayIndex];
                            if (!data) return null;
                            return (
                                <div
                                    key={dayIndex}
                                    className={cn("w-2.5 h-2.5 rounded-sm transition-colors hover:ring-1 hover:ring-white/50 cursor-pointer", getColor(data.count))}
                                    title={`${data.date}: ${data.count} papers`}
                                />
                            );
                        })}
                    </div>
                ))}
            </div>
            <div className="flex items-center gap-2 mt-2 text-[10px] text-slate-500 justify-end">
                <span>少</span>
                <div className="flex gap-1">
                    <div className="w-2.5 h-2.5 rounded-sm bg-slate-900"></div>
                    <div className="w-2.5 h-2.5 rounded-sm bg-emerald-900/40"></div>
                    <div className="w-2.5 h-2.5 rounded-sm bg-emerald-700/60"></div>
                    <div className="w-2.5 h-2.5 rounded-sm bg-emerald-500/80"></div>
                    <div className="w-2.5 h-2.5 rounded-sm bg-emerald-400"></div>
                </div>
                <span>多</span>
            </div>
        </div>
    );
};
