import React from 'react';
import { Brain, Target } from 'lucide-react';
import type { UserProfile } from '../../../types/user';

interface MemoryDashboardProps {
    userProfile: UserProfile;
}

export const MemoryDashboard: React.FC<MemoryDashboardProps> = ({ userProfile }) => {
    const { focus, context } = userProfile;

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Brain className="text-indigo-400" />
                记忆与偏好概览
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                    <div className="text-slate-500 text-xs mb-1">关注领域</div>
                    <div className="text-xl font-bold text-white">{focus.category.length} 个主题</div>
                </div>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                    <div className="text-slate-500 text-xs mb-1">关键词</div>
                    <div className="text-xl font-bold text-white">{focus.keywords.length} 个</div>
                </div>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                    <div className="text-slate-500 text-xs mb-1">当前任务</div>
                    <div className="text-sm font-medium text-white truncate" title={context.currentTask}>{context.currentTask || '未设置'}</div>
                </div>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                    <div className="text-slate-500 text-xs mb-1">未来目标</div>
                    <div className="text-sm font-medium text-white truncate" title={context.futureGoal}>{context.futureGoal || '未设置'}</div>
                </div>
            </div>

            <div className="space-y-4">
                <div>
                    <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                        <Target size={14} /> 知识图谱节点
                    </h3>
                    <div className="flex flex-wrap gap-2">
                        {focus.category.map((cat, i) => (
                            <span key={i} className="px-2 py-1 bg-indigo-950/30 text-indigo-300 text-xs rounded border border-indigo-500/20">
                                {cat}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
