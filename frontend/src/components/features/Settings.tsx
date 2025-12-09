import React, { useState, useEffect } from 'react';
import { supabase } from '../../services/supabase';
import { UserAPI } from '../../services/api';
import type { UserProfile } from '../../types/user';
import { Avatar } from '../common/Avatar';
import { TagInput } from '../common/TagInput';
import { CategorySelector } from '../common/CategorySelector';
import { ArrowLeft, Sparkles, Lightbulb, Save, LogOut, User } from 'lucide-react';

interface SettingsProps {
    userProfile: UserProfile | null;
    onUpdate: () => void;
    onBack?: () => void;
}

export function Settings({ userProfile, onUpdate, onBack }: SettingsProps) {
    if (!userProfile) return null;

    const [loading, setLoading] = useState(false);
    const [nlLoading, setNlLoading] = useState(false);
    const [nlInput, setNlInput] = useState('');

    const [formData, setFormData] = useState({
        nickname: '',
        avatar: '',
        role: '',
        stage: '',
        preferences: '',
        category: [] as string[],
        keywords: [] as string[],
        authors: [] as string[],
        institutions: [] as string[],
        email: '',
        receive_email: true,
    });

    useEffect(() => {
        if (userProfile) {
            setFormData({
                nickname: userProfile.info?.name || '',
                avatar: userProfile.info?.avatar || '',
                role: userProfile.info?.role || '',
                stage: userProfile.context?.stage || '',
                preferences: userProfile.context?.preferences || '',
                category: userProfile.focus?.category || [],
                keywords: userProfile.focus?.keywords || [],
                authors: userProfile.focus?.authors || [],
                institutions: userProfile.focus?.institutions || [],
                email: userProfile.info?.email || '',
                receive_email: userProfile.info?.receive_email ?? true,
            });
        }
    }, [userProfile]);

    const handleSave = async () => {
        setLoading(true);
        try {
            const updates = {
                info: {
                    name: formData.nickname,
                    nickname: formData.nickname,
                    avatar: formData.avatar,
                    role: formData.role,
                    email: formData.email,
                    receive_email: formData.receive_email
                },
                context: {
                    stage: formData.stage,
                    preferences: formData.preferences,
                    currentTask: userProfile?.context?.currentTask || '',
                    futureGoal: userProfile?.context?.futureGoal || '',
                    learningMode: userProfile?.context?.learningMode || 'basic',
                },
                focus: {
                    category: formData.category,
                    keywords: formData.keywords,
                    authors: formData.authors,
                    institutions: formData.institutions,
                }
            };

            await UserAPI.updateProfile(updates);
            alert('保存成功');
            onUpdate();
        } catch (error) {
            console.error('Error updating settings:', error);
            alert('保存失败');
        } finally {
            setLoading(false);
        }
    };

    const handleNLUpdate = async () => {
        if (!nlInput.trim()) return;
        setNlLoading(true);
        try {
            await UserAPI.updateProfileNL(nlInput);
            setNlInput('');
            alert('更新成功');
            onUpdate(); // Refresh profile to show changes
        } catch (error) {
            console.error('Error updating profile via NL:', error);
            alert('更新失败');
        } finally {
            setNlLoading(false);
        }
    };

    const handleLogout = async () => {
        await supabase.auth.signOut();
        window.location.reload();
    };

    return (
        <div className="p-6 max-w-6xl mx-auto space-y-6 pb-20 animate-in fade-in">
            <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-4">
                    {onBack && (
                        <button
                            onClick={onBack}
                            className="p-2 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors"
                        >
                            <ArrowLeft size={24} />
                        </button>
                    )}
                    <h1 className="text-2xl font-bold text-white">设置</h1>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                    >
                        <LogOut size={16} />
                        退出登录
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={loading}
                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-6 rounded-lg shadow-lg shadow-blue-900/20 disabled:opacity-50 transition-all"
                    >
                        <Save size={16} />
                        {loading ? '保存中...' : '保存更改'}
                    </button>
                </div>
            </div>

            {/* 基础设置 - 合并基本资料和邮件设置 */}
            <section className="bg-slate-900/50 rounded-xl p-6 border border-slate-800 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-6 text-slate-400">
                    <User size={20} />
                    <h2 className="text-lg font-semibold text-white">基础设置</h2>
                </div>
                <div className="flex items-start gap-8">
                    {/* 左侧：头像上传 */}
                    <div className="flex flex-col items-center gap-3">
                        <div className="relative group cursor-pointer">
                            <input
                                type="file"
                                accept="image/*"
                                onChange={async (e) => {
                                    const file = e.target.files?.[0];
                                    if (!file) return;

                                    try {
                                        setLoading(true);
                                        const fileExt = file.name.split('.').pop();
                                        const fileName = `${userProfile?.info?.name || 'user'}-${Date.now()}.${fileExt}`;
                                        const filePath = `${fileName}`;

                                        const { error: uploadError } = await supabase.storage
                                            .from('avatars')
                                            .upload(filePath, file);

                                        if (uploadError) {
                                            throw uploadError;
                                        }

                                        const { data } = supabase.storage
                                            .from('avatars')
                                            .getPublicUrl(filePath);

                                        setFormData(prev => ({ ...prev, avatar: data.publicUrl }));
                                        alert('头像上传成功，请点击保存以应用更改');
                                    } catch (error: any) {
                                        console.error('Error uploading avatar:', error);
                                        alert(`头像上传失败: ${error.message || '请确保您已登录且网络正常'}`);
                                    } finally {
                                        setLoading(false);
                                    }
                                }}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                            />
                            {formData.avatar ? (
                                <img src={formData.avatar} alt="Avatar" className="w-24 h-24 rounded-full object-cover border-4 border-slate-800 shadow-lg group-hover:opacity-75 transition-opacity" />
                            ) : (
                                <div className="w-24 h-24 group-hover:opacity-75 transition-opacity">
                                    <Avatar name={formData.nickname} size="xl" />
                                </div>
                            )}
                            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                                <span className="bg-black/50 text-white text-xs px-2 py-1 rounded">更换头像</span>
                            </div>
                        </div>
                        <span className="text-xs text-slate-500">点击头像更换</span>
                    </div>

                    {/* 右侧：昵称、邮箱、邮件推送 */}
                    <div className="flex-1 space-y-4 max-w-md">
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">昵称</label>
                            <input
                                type="text"
                                value={formData.nickname}
                                onChange={e => setFormData({ ...formData, nickname: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-blue-500 outline-none transition-colors"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">接收邮箱</label>
                            <input
                                type="email"
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-blue-500 outline-none transition-colors"
                                placeholder="your@email.com"
                            />
                        </div>

                        <div>
                            <div className="text-sm font-medium text-white">每日报告推送</div>
                            <div className="text-xs text-slate-500">每天自动发送最新论文报告到您的邮箱</div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={formData.receive_email}
                                onChange={(e) => setFormData({ ...formData, receive_email: e.target.checked })}
                                className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-slate-700 rounded-full peer peer-checked:bg-blue-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                        </label>
                    </div>
                </div>
        </div>
            </section >

        {/* Natural Language Adjustment */ }
        < section className = "bg-slate-900/50 rounded-xl p-6 border border-slate-800 backdrop-blur-sm" >
                <div className="flex items-center gap-2 mb-4 text-blue-400">
                    <Sparkles size={20} />
                    <h2 className="text-lg font-semibold text-white">自然语言调整</h2>
                </div>
                <div className="flex gap-4">
                    <input
                        type="text"
                        value={nlInput}
                        onChange={e => setNlInput(e.target.value)}
                        placeholder="告诉 Agent 您最近想关注什么，例如: '最近想了解一下 RAG 在医疗领域的应用'..."
                        className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                        onKeyDown={e => e.key === 'Enter' && handleNLUpdate()}
                    />
                    <button
                        onClick={handleNLUpdate}
                        disabled={nlLoading || !nlInput.trim()}
                        className="bg-slate-800 hover:bg-slate-700 text-white px-6 py-2 rounded-lg border border-slate-700 font-medium transition-colors disabled:opacity-50 whitespace-nowrap"
                    >
                        {nlLoading ? '更新中...' : '更新'}
                    </button>
                </div>
                <p className="text-xs text-slate-500 mt-3 ml-1">
                    Agent 会分析您的输入，自动更新关注类别、关键词等信息。
                </p>
            </section >

        {/* Focus Areas */ }
        < section className = "bg-slate-900/50 rounded-xl p-6 border border-slate-800 backdrop-blur-sm" >
                <div className="flex items-center gap-2 mb-6 text-indigo-400">
                    <Lightbulb size={20} />
                    <h2 className="text-lg font-semibold text-white">关注什么</h2>
                </div>

                <div className="space-y-8">
                    {/* 1. Category (ArXiv Categories) */}
                    <CategorySelector
                        selectedCategories={formData.category}
                        onChange={categories => setFormData({ ...formData, category: categories })}
                    />

                    {/* 2. Keywords */}
                    <TagInput
                        label="关键词 (Keywords)"
                        tags={formData.keywords}
                        onChange={tags => setFormData({ ...formData, keywords: tags })}
                        placeholder="输入关键词并回车..."
                        addButtonText="添加关键词"
                    />

                    {/* 3. Authors */}
                    <TagInput
                        label="关注作者 (Authors)"
                        tags={formData.authors}
                        onChange={tags => setFormData({ ...formData, authors: tags })}
                        placeholder="输入作者姓名并回车..."
                        addButtonText="添加作者"
                    />

                    {/* 4. Institutions */}
                    <TagInput
                        label="关注机构 (Institutions)"
                        tags={formData.institutions}
                        onChange={tags => setFormData({ ...formData, institutions: tags })}
                        placeholder="输入机构名称并回车..."
                        addButtonText="添加机构"
                    />
                </div>
            </section >
        </div >
    );
}
