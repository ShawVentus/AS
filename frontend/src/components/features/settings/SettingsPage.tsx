import React, { useState } from 'react';
import { Save, User, Brain, Target, BookOpen, Mail, Hash, X, MessageSquare, Loader2 } from 'lucide-react';
import { USER_PROFILE } from '../../../data/mockData';
import { UserAPI } from '../../../services/api';

export const SettingsPage = () => {
    const [activeTab, setActiveTab] = useState('memory');
    const [learningMode, setLearningMode] = useState<'basic' | 'innovation'>(USER_PROFILE.context.learningMode);
    const [nlInput, setNlInput] = useState('');
    const [isUpdatingNL, setIsUpdatingNL] = useState(false);

    const handleNLUpdate = async () => {
        if (!nlInput.trim()) return;
        setIsUpdatingNL(true);
        try {
            // Mock user ID for now
            await UserAPI.updateNL(nlInput, 'user_123');
            setNlInput('');
            // In a real app, we would reload the profile here
            alert('画像已更新 (Mock)');
        } catch (error) {
            console.error('Failed to update profile:', error);
            alert('更新失败');
        } finally {
            setIsUpdatingNL(false);
        }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto animate-in fade-in pb-20">
            <h1 className="text-2xl font-bold text-white mb-6">全局设置</h1>

            <div className="flex gap-6 mb-8 border-b border-slate-800">
                <button
                    onClick={() => setActiveTab('memory')}
                    className={`pb-3 px-1 text-sm font-medium transition-colors relative ${activeTab === 'memory' ? 'text-cyan-400' : 'text-slate-400 hover:text-slate-200'}`}
                >
                    记忆管理
                    {activeTab === 'memory' && <span className="absolute bottom-0 left-0 w-full h-0.5 bg-cyan-400 rounded-full"></span>}
                </button>
                <button
                    onClick={() => setActiveTab('profile')}
                    className={`pb-3 px-1 text-sm font-medium transition-colors relative ${activeTab === 'profile' ? 'text-cyan-400' : 'text-slate-400 hover:text-slate-200'}`}
                >
                    个人信息
                    {activeTab === 'profile' && <span className="absolute bottom-0 left-0 w-full h-0.5 bg-cyan-400 rounded-full"></span>}
                </button>
            </div>

            {activeTab === 'memory' && (
                <div className="space-y-8">
                    {/* Natural Language Update */}
                    <section className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <MessageSquare className="text-cyan-400" size={20} /> 自然语言调整
                        </h2>
                        <div className="flex gap-4">
                            <input
                                type="text"
                                value={nlInput}
                                onChange={(e) => setNlInput(e.target.value)}
                                placeholder="告诉 Agent 您最近想关注什么，例如：'最近想了解一下 RAG 在医疗领域的应用'..."
                                className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none"
                                onKeyDown={(e) => e.key === 'Enter' && handleNLUpdate()}
                            />
                            <button
                                onClick={handleNLUpdate}
                                disabled={isUpdatingNL || !nlInput.trim()}
                                className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                            >
                                {isUpdatingNL ? <Loader2 size={18} className="animate-spin" /> : '更新'}
                            </button>
                        </div>
                        <p className="mt-2 text-xs text-slate-500">
                            Agent 会分析您的输入，自动更新关注类别、关键词等信息。
                        </p>
                    </section>

                    {/* Learning Mode */}
                    <section className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <Brain className="text-cyan-400" size={20} /> 学习模式
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div
                                onClick={() => setLearningMode('basic')}
                                className={`cursor-pointer p-4 rounded-lg border transition-all ${learningMode === 'basic' ? 'bg-cyan-950/30 border-cyan-500/50 ring-1 ring-cyan-500/20' : 'bg-slate-950 border-slate-800 hover:border-slate-700'}`}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className={`font-bold ${learningMode === 'basic' ? 'text-cyan-400' : 'text-slate-200'}`}>基础学习</h3>
                                    {learningMode === 'basic' && <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.5)]"></span>}
                                </div>
                                <p className="text-xs text-slate-400 leading-relaxed">
                                    适合刚接触新领域的阶段。优先推荐综述、高引用经典论文，帮助快速建立知识体系。
                                </p>
                            </div>
                            <div
                                onClick={() => setLearningMode('innovation')}
                                className={`cursor-pointer p-4 rounded-lg border transition-all ${learningMode === 'innovation' ? 'bg-purple-950/30 border-purple-500/50 ring-1 ring-purple-500/20' : 'bg-slate-950 border-slate-800 hover:border-slate-700'}`}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className={`font-bold ${learningMode === 'innovation' ? 'text-purple-400' : 'text-slate-200'}`}>创新发现</h3>
                                    {learningMode === 'innovation' && <span className="w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_8px_rgba(192,132,252,0.5)]"></span>}
                                </div>
                                <p className="text-xs text-slate-400 leading-relaxed">
                                    适合寻找Idea的阶段。优先推荐最新预印本、跨领域交叉研究，激发创新灵感。
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* Focus Areas */}
                    <section className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                        <h2 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                            <Target className="text-emerald-400" size={20} /> 关注什么
                        </h2>

                        <div className="space-y-6">
                            <div>
                                <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                                    <span className="w-1 h-4 bg-emerald-500 rounded-full"></span> 领域 (Domains)
                                    <span className="text-xs text-slate-500 font-normal ml-auto">论文检索页面</span>
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                    {USER_PROFILE.focus.domains.map(domain => (
                                        <span key={domain} className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-sm text-slate-300 flex items-center gap-2">
                                            {domain} <button className="text-slate-500 hover:text-red-400"><X size={12} /></button>
                                        </span>
                                    ))}
                                    <button className="px-3 py-1.5 border border-dashed border-slate-700 rounded text-sm text-slate-500 hover:text-slate-300 hover:border-slate-500 transition-colors">+ 添加领域</button>
                                </div>
                            </div>

                            <div>
                                <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                                    <span className="w-1 h-4 bg-emerald-500 rounded-full"></span> 关键词 (Keywords)
                                    <span className="text-xs text-slate-500 font-normal ml-auto">论文筛选依据</span>
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                    {USER_PROFILE.focus.keywords.map(kw => (
                                        <span key={kw} className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-sm text-slate-300 flex items-center gap-2">
                                            {kw} <button className="text-slate-500 hover:text-red-400"><X size={12} /></button>
                                        </span>
                                    ))}
                                    <button className="px-3 py-1.5 border border-dashed border-slate-700 rounded text-sm text-slate-500 hover:text-slate-300 hover:border-slate-500 transition-colors">+ 添加关键词</button>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <div>
                                        <label className="block text-xs font-medium text-slate-500 mb-1">偏向</label>
                                        <div className="flex gap-4 mt-2">
                                            <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                                                <input type="radio" name="orientation" defaultChecked={true} className="accent-indigo-500" /> 应用
                                            </label>
                                            <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                                                <input type="radio" name="orientation" className="accent-indigo-500" /> 科研
                                            </label>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            )}

            {activeTab === 'profile' && (
                <div className="space-y-8">
                    <section className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                        <h2 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                            <User className="text-cyan-400" size={20} /> 基本信息
                        </h2>

                        <div className="flex items-start gap-8">
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-24 h-24 rounded-full overflow-hidden border-2 border-slate-700 bg-slate-800">
                                    <img src={USER_PROFILE.info.avatar} alt="Avatar" className="w-full h-full object-cover" />
                                </div>
                                <button className="text-xs text-cyan-400 hover:text-cyan-300">更换头像</button>
                            </div>

                            <div className="flex-1 space-y-4 max-w-md">
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
                                        <Hash size={12} /> 昵称
                                    </label>
                                    <input type="text" defaultValue={USER_PROFILE.info.name} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none" />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
                                        <Mail size={12} /> 邮箱地址
                                    </label>
                                    <input type="email" defaultValue={USER_PROFILE.info.email} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none" />
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            )}

            <div className="mt-8 flex justify-end">
                <button className="flex items-center gap-2 px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg transition-colors shadow-lg shadow-cyan-900/20">
                    <Save size={18} /> 保存更改
                </button>
            </div>
        </div>
    );
};
