import React, { useState } from 'react';
import { supabase } from '../../services/supabase';
import type { UserProfile } from '../../types/user';

interface OnboardingProps {
    onComplete: () => void;
    initialName?: string;
}

export const Onboarding: React.FC<OnboardingProps> = ({ onComplete, initialName }) => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        nickname: initialName || '',
        role: '',
        stage: '',
        purpose: [] as string[],
        domains: [] as string[],
        keywords: '',
    });

    const handleUpdateProfile = async () => {
        setLoading(true);
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error('No user found');

            const updates = {
                info: {
                    name: formData.nickname, // Using nickname as display name
                    nickname: formData.nickname,
                    email: user.email,
                    avatar: '',
                    role: formData.role
                },
                context: {
                    stage: formData.stage,
                    purpose: formData.purpose,
                    learningMode: 'basic'
                },
                focus: {
                    domains: formData.domains,
                    keywords: formData.keywords.split(/[,，]/).map(k => k.trim()).filter(Boolean),
                    authors: [],
                    institutions: []
                },
                updated_at: new Date().toISOString(),
            };

            const { error } = await supabase
                .from('profiles')
                .update(updates)
                .eq('user_id', user.id);

            if (error) throw error;
            onComplete();
        } catch (error) {
            console.error('Error updating profile:', error);
            alert('保存失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    const renderStep1 = () => (
        <div className="space-y-6">
            <h3 className="text-xl font-bold text-white">基本信息</h3>
            <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">昵称</label>
                <input
                    type="text"
                    value={formData.nickname}
                    onChange={e => setFormData({ ...formData, nickname: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white"
                    placeholder="如何称呼您？"
                />
            </div>
            <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">身份角色</label>
                <select
                    value={formData.role}
                    onChange={e => setFormData({ ...formData, role: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white"
                >
                    <option value="">请选择...</option>
                    <option value="student">学生 (本科/硕士/博士)</option>
                    <option value="researcher">科研人员</option>
                    <option value="engineer">工程师</option>
                    <option value="other">其他</option>
                </select>
            </div>
            <button
                onClick={() => setStep(2)}
                disabled={!formData.nickname || !formData.role}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
            >
                下一步
            </button>
        </div>
    );

    const renderStep2 = () => (
        <div className="space-y-6">
            <h3 className="text-xl font-bold text-white">科研背景</h3>
            <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">当前阶段</label>
                <select
                    value={formData.stage}
                    onChange={e => setFormData({ ...formData, stage: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white"
                >
                    <option value="">请选择...</option>
                    <option value="undergrad">本科生</option>
                    <option value="master1">研一</option>
                    <option value="master2">研二</option>
                    <option value="master3">研三</option>
                    <option value="phd1">博一</option>
                    <option value="phd_senior">博二及以上</option>
                    <option value="work">工作</option>
                </select>
            </div>
            <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">阅读目的 (多选)</label>
                <div className="space-y-2">
                    {['寻找灵感', '跟进前沿', '解决具体问题', '系统学习'].map(p => (
                        <label key={p} className="flex items-center space-x-2 text-slate-300">
                            <input
                                type="checkbox"
                                checked={formData.purpose.includes(p)}
                                onChange={e => {
                                    const newPurpose = e.target.checked
                                        ? [...formData.purpose, p]
                                        : formData.purpose.filter(item => item !== p);
                                    setFormData({ ...formData, purpose: newPurpose });
                                }}
                                className="rounded border-slate-700 bg-slate-800 text-indigo-600"
                            />
                            <span>{p}</span>
                        </label>
                    ))}
                </div>
            </div>
            <div className="flex gap-4">
                <button
                    onClick={() => setStep(1)}
                    className="w-1/3 bg-slate-700 hover:bg-slate-600 text-white font-bold py-2 px-4 rounded"
                >
                    上一步
                </button>
                <button
                    onClick={() => setStep(3)}
                    disabled={!formData.stage || formData.purpose.length === 0}
                    className="w-2/3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
                >
                    下一步
                </button>
            </div>
        </div>
    );

    const renderStep3 = () => (
        <div className="space-y-6">
            <h3 className="text-xl font-bold text-white">关注领域</h3>
            <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">关注领域 (多选)</label>
                <div className="grid grid-cols-2 gap-2">
                    {['CV', 'NLP', 'RL', 'Robotics', 'GNN', 'Multimodal', 'Theory', 'Systems'].map(d => (
                        <label key={d} className="flex items-center space-x-2 text-slate-300">
                            <input
                                type="checkbox"
                                checked={formData.domains.includes(d)}
                                onChange={e => {
                                    const newDomains = e.target.checked
                                        ? [...formData.domains, d]
                                        : formData.domains.filter(item => item !== d);
                                    setFormData({ ...formData, domains: newDomains });
                                }}
                                className="rounded border-slate-700 bg-slate-800 text-indigo-600"
                            />
                            <span>{d}</span>
                        </label>
                    ))}
                </div>
            </div>
            <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">关键词 (用逗号分隔)</label>
                <textarea
                    value={formData.keywords}
                    onChange={e => setFormData({ ...formData, keywords: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white h-24"
                    placeholder="例如: transformer, diffusion models, contrastive learning"
                />
            </div>
            <div className="flex gap-4">
                <button
                    onClick={() => setStep(2)}
                    className="w-1/3 bg-slate-700 hover:bg-slate-600 text-white font-bold py-2 px-4 rounded"
                >
                    上一步
                </button>
                <button
                    onClick={handleUpdateProfile}
                    disabled={loading || formData.domains.length === 0}
                    className="w-2/3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
                >
                    {loading ? '保存中...' : '完成初始化'}
                </button>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
            <div className="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-lg p-8 shadow-xl">
                <div className="mb-8">
                    <div className="flex justify-between items-center text-sm text-slate-500 mb-2">
                        <span>Step {step} of 3</span>
                        <span>{Math.round((step / 3) * 100)}%</span>
                    </div>
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-indigo-500 transition-all duration-300"
                            style={{ width: `${(step / 3) * 100}%` }}
                        />
                    </div>
                </div>

                {step === 1 && renderStep1()}
                {step === 2 && renderStep2()}
                {step === 3 && renderStep3()}
            </div>
        </div>
    );
};
