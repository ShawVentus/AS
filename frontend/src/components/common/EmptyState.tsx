import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
    icon: LucideIcon;
    title: string;
    description: string;
    action?: {
        label: string;
        onClick: () => void;
    };
    className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
    icon: Icon,
    title,
    description,
    action,
    className = ''
}) => (
    <div className={`flex flex-col items-center justify-center py-12 px-4 animate-in fade-in zoom-in-95 duration-300 ${className}`}>
        <div className="bg-slate-800/50 p-4 rounded-full mb-4">
            <Icon className="text-slate-500" size={32} />
        </div>
        <h3 className="text-slate-200 font-semibold mb-2 text-lg">{title}</h3>
        <p className="text-slate-500 text-sm text-center max-w-md mb-6 leading-relaxed">
            {description}
        </p>
        {action && (
            <button
                onClick={action.onClick}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition-all shadow-lg shadow-indigo-900/20 active:scale-95"
            >
                {action.label}
            </button>
        )}
    </div>
);
