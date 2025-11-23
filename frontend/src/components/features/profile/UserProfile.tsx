import React, { useState } from 'react';
import { Brain, Settings, Compass, Microscope, X, Plus } from 'lucide-react';
import { USER_PROFILE } from '../../../data/mockData';
import { cn } from '../../../utils/cn';

interface UserMenuProps {
    onNavigate: (view: string) => void;
}

export const UserMenu: React.FC<UserMenuProps> = ({ onNavigate }) => {
    const [isHovered, setIsHovered] = useState(false);
    const [learningMode, setLearningMode] = useState(USER_PROFILE.context.learningMode);

    const handleModeChange = (mode: 'basic' | 'innovation') => {
        setLearningMode(mode);
        // In a real app, this would update the backend/context
    };

    return (
        <div className="relative z-50" onMouseEnter={() => setIsHovered(true)} onMouseLeave={() => setIsHovered(false)}>
            <div className="flex items-center gap-3 cursor-pointer py-2">
                <div className="text-right hidden md:block leading-tight">
                    <div className="text-xs font-bold text-slate-300">{USER_PROFILE.info.name}</div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-wide">{USER_PROFILE.context.stage}</div>
                </div>
                <div className="relative">
                    <img src={USER_PROFILE.info.avatar} alt="avatar" className="w-8 h-8 rounded-full border border-slate-700 bg-slate-800" />
                    <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-slate-950"></div>
                </div>
            </div>

            {isHovered && (
                <div className="absolute right-0 top-full pt-1 w-96 animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="bg-slate-950 border border-slate-800 rounded-xl shadow-2xl overflow-hidden ring-1 ring-black/50">
                        <div className="bg-slate-900/50 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                            <h3 className="text-slate-300 font-semibold text-xs flex items-center gap-2"><Brain size={14} className="text-cyan-400" /> 记忆与偏好</h3>
                            <span className="text-[10px] bg-cyan-950 text-cyan-400 px-1.5 py-0.5 rounded border border-cyan-900">ACTIVE</span>
                        </div>
                        <div className="flex divide-x divide-slate-800">
                            <div className="w-2/3 p-4 space-y-4">
                                <div>
                                    <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1.5 block">关注领域</label>
                                    <div className="flex flex-wrap gap-1.5">
                                        {USER_PROFILE.focus.domains.map(d => <span key={d} className="text-[10px] bg-indigo-950/50 text-indigo-300 px-1.5 py-0.5 rounded border border-indigo-500/10">{d}</span>)}
                                        {USER_PROFILE.focus.keywords.map(k => <span key={k} className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">{k}</span>)}
                                    </div>
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1.5 block">当前模式</label>
                                    <div className="flex bg-slate-900 p-1 rounded border border-slate-800/50">
                                        <button
                                            onClick={() => handleModeChange('basic')}
                                            className={cn("flex-1 text-[10px] py-1 rounded transition-colors", learningMode === 'basic' ? "bg-emerald-900/30 text-emerald-400 font-medium" : "text-slate-500 hover:text-slate-300")}
                                        >基础学习</button>
                                        <button
                                            onClick={() => handleModeChange('innovation')}
                                            className={cn("flex-1 text-[10px] py-1 rounded transition-colors", learningMode === 'innovation' ? "bg-purple-900/30 text-purple-400 font-medium" : "text-slate-500 hover:text-slate-300")}
                                        >创新发现</button>
                                    </div>
                                    <p className="text-[10px] text-slate-500 mt-1.5 leading-relaxed">
                                        {learningMode === 'basic' ? "侧重基础概念、经典综述与精读建议。" : "侧重最新Idea、SOTA对比与快速筛选。"}
                                    </p>
                                </div>
                            </div>
                            <div className="w-1/3 bg-slate-900/30 p-4 flex flex-col justify-between">
                                <div className="space-y-2">
                                    <div className="text-center mb-2">
                                        <img src={USER_PROFILE.info.avatar} className="w-10 h-10 rounded-full mx-auto mb-1 border border-slate-700" alt="profile" />
                                        <h4 className="text-slate-200 text-xs font-medium">{USER_PROFILE.info.name}</h4>
                                    </div>
                                    <button onClick={() => onNavigate('settings')} className="w-full text-left text-[11px] text-slate-400 hover:text-white flex items-center gap-1.5"><Settings size={12} /> 管理信息</button>
                                </div>
                                <button className="w-full mt-2 py-1 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700">退出</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
