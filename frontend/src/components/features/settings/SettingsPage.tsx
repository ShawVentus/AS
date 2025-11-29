import React, { useState } from 'react';
import { Save, User, Target, BookOpen, Mail, Hash, X, MessageSquare, Loader2 } from 'lucide-react';
import { UserAPI } from '../../../services/api';
import type { UserProfile } from '../../../types';

interface SettingsPageProps {
    userProfile: UserProfile | null;
    onUpdate: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ userProfile, onUpdate }) => {
    const [activeTab, setActiveTab] = useState('memory');
    const [nlInput, setNlInput] = useState('');
    const [isUpdatingNL, setIsUpdatingNL] = useState(false);

    const handleNLUpdate = async () => {
        if (!nlInput.trim()) return;
        setIsUpdatingNL(true);
        try {
            await UserAPI.updateProfileNL(nlInput);
            setNlInput('');
            alert('画像已更新');
            onUpdate();
        } catch (error) {
            console.error('Failed to update profile:', error);
            alert('更新失败');
        } finally {
            setIsUpdatingNL(false);
        }
    };

    if (!userProfile) {
        return (
            <div className="p-6 max-w-4xl mx-auto animate-in fade-in pb-20">
                <div className="text-center text-slate-400 py-10">
                    加载中...
                </div>
            </div>
        );
    }

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

                    {/* Focus Areas */}
                    <section className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                        <h2 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                            <Target className="text-emerald-400" size={20} /> 关注什么
                        </h2>

                        <div className="space-y-6">
                            <div>
                                <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                                    <span className="w-1 h-4 bg-emerald-500 rounded-full"></span> 关注领域 (Category)
                                    <span className="text-xs text-slate-500 font-normal ml-auto">论文检索页面</span>
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                    {(userProfile.focus?.category || []).map(cat => (
                                        <span key={cat} className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-sm text-slate-300 flex items-center gap-2">
                                            {cat} <button className="text-slate-500 hover:text-red-400"><X size={12} /></button>
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
                                    {(userProfile.focus?.keywords || []).map(kw => (
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
                                    {userProfile.info?.avatar ? (
                                        <img src={userProfile.info.avatar} alt="Avatar" className="w-full h-full object-cover" />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-slate-500">
                                            <User size={48} />
                                        </div>
                                    )}
                                </div>
                                <button className="text-xs text-cyan-400 hover:text-cyan-300">更换头像</button>
                            </div>

                            <div className="flex-1 space-y-4 max-w-md">
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
                                        <Hash size={12} /> 昵称
                                    </label>
                                    <input type="text" defaultValue={userProfile.info?.name || ''} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none" />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
                                        <Mail size={12} /> 邮箱地址
                                    </label>
                                    <input type="email" defaultValue={userProfile.info?.email || ''} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none" />
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
