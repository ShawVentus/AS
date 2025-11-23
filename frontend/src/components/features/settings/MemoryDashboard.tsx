import React from 'react';
import { UserProfile } from '../../../types';
import { Brain, Hash, Target, Zap } from 'lucide-react';

interface MemoryDashboardProps {
    profile: UserProfile;
}

export function MemoryDashboard({ profile }: MemoryDashboardProps) {
    const { focus, context, memory } = profile;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-lg flex items-center gap-4">
                    <div className="p-3 bg-blue-500/10 rounded-full text-blue-400">
                        <Target size={24} />
                    </div>
                    <div>
                        <div className="text-sm text-slate-500">关注领域</div>
                        <div className="text-xl font-bold text-white">{focus.domains.length} 个主题</div>
                    </div>
                </div>
                <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-lg flex items-center gap-4">
                    <div className="p-3 bg-purple-500/10 rounded-full text-purple-400">
                        <Hash size={24} />
                    </div>
                    <div>
                        <div className="text-sm text-slate-500">关键词</div>
                        <div className="text-xl font-bold text-white">{focus.keywords.length} 个</div>
                    </div>
                </div>
                <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-lg flex items-center gap-4">
                    <div className="p-3 bg-amber-500/10 rounded-full text-amber-400">
                        <Brain size={24} />
                    </div>
                    <div>
                        <div className="text-sm text-slate-500">已读论文</div>
                        <div className="text-xl font-bold text-white">{memory.readPapers.length} 篇</div>
                    </div>
                </div>
            </div>

            {/* Focus Areas */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <Target size={20} className="text-blue-400" />
                    研究关注点 (Focus)
                </h3>
                <div className="space-y-4">
                    <div>
                        <div className="text-sm text-slate-500 mb-2">主要领域</div>
                        <div className="flex flex-wrap gap-2">
                            {focus.domains.map((domain, i) => (
                                <span key={i} className="px-3 py-1 bg-blue-500/10 text-blue-300 rounded-full text-sm border border-blue-500/20">
                                    {domain}
                                </span>
                            ))}
                        </div>
                    </div>
                    <div>
                        <div className="text-sm text-slate-500 mb-2">关键词</div>
                        <div className="flex flex-wrap gap-2">
                            {focus.keywords.map((kw, i) => (
                                <div key={i} className="flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full border border-slate-700">
                                    <span className="text-slate-200 text-sm">{kw}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Context & Memory */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Context */}
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                        <Zap size={20} className="text-yellow-400" />
                        当前上下文 (Context)
                    </h3>
                    <div className="space-y-4">
                        <div>
                            <div className="text-sm text-slate-500 mb-1">研究阶段</div>
                            <div className="text-white">{context.stage}</div>
                        </div>
                        <div>
                            <div className="text-sm text-slate-500 mb-1">当前任务</div>
                            <div className="text-white">{context.currentTask}</div>
                        </div>
                        <div>
                            <div className="text-sm text-slate-500 mb-1">未来目标</div>
                            <div className="text-white">{context.futureGoal}</div>
                        </div>
                    </div>
                </div>

                {/* Long Term Memory (Read Papers) */}
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                        <Brain size={20} className="text-purple-400" />
                        已读论文 (Memory)
                    </h3>
                    <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-700">
                        {memory.readPapers.map((item, i) => (
                            <div key={i} className="p-3 bg-slate-800/50 rounded border border-slate-700/50 text-sm text-slate-300">
                                Paper ID: {item}
                            </div>
                        ))}
                        {memory.readPapers.length === 0 && (
                            <div className="text-slate-500 text-center py-4">暂无阅读记录</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
