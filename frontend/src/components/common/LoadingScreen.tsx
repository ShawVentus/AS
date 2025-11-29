import React from 'react';
import { BookOpen } from 'lucide-react';

export const LoadingScreen: React.FC = () => {
    return (
        <div className="fixed inset-0 bg-slate-950 flex flex-col items-center justify-center z-[100] animate-in fade-in duration-300">
            <div className="relative">
                <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-900/50 animate-bounce">
                    <BookOpen className="text-white w-8 h-8" />
                </div>
                <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 w-12 h-1 bg-blue-500/20 rounded-full blur-sm animate-pulse"></div>
            </div>

            <h1 className="mt-8 text-2xl font-bold text-white tracking-tight">
                ArxivScout
            </h1>
            <p className="mt-2 text-slate-500 text-sm animate-pulse">
                正在准备您的科研助手...
            </p>
        </div>
    );
};
