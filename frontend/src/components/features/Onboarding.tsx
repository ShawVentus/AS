import React, { useState } from 'react';
import { supabase } from '../../services/supabase';
import { UserAPI } from '../../services/api';
import { CategorySelector } from '../common/CategorySelector';
import { TagInput } from '../common/TagInput';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';

interface OnboardingProps {
    onComplete: () => void;
    initialName?: string;
}

export const Onboarding: React.FC<OnboardingProps> = ({ onComplete, initialName }) => {
    console.log("Onboarding component mounted");
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        // Step 1: 偏好与类别
        preferences: '',
        category: [] as string[],
        // Step 2: 特别关注
        keywords: [] as string[],
        authors: [] as string[],
        institutions: [] as string[],
        // Step 3: 现状与目标
        currentTask: '',
        futureGoal: '',
        // Hidden/Default
        nickname: initialName || '',
        role: 'researcher'
    });

    const handleUpdateProfile = async () => {
        setLoading(true);
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error('No user found');

            // 构造初始化请求数据
            const initData = {
                info: {
                    id: user.id,
                    name: formData.nickname,
                    nickname: formData.nickname,
                    email: user.email || '',
                    avatar: '',
                    role: formData.role
                },
                focus: {
                    category: formData.category,
                    keywords: formData.keywords,
                    authors: formData.authors,
                    institutions: formData.institutions
                },
                context: {
                    preferences: formData.preferences,
                    currentTask: formData.currentTask,
                    futureGoal: formData.futureGoal
                }
            };

            // 调用后端 API 进行初始化
            // 这将确保在后端创建/更新 Profile，并处理任何必要的关联逻辑
            await UserAPI.initialize(initData);

            onComplete();
        } catch (error) {
            console.error('Error updating profile:', error);
            alert('保存失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    // 进度条组件
    const ProgressBar = () => (
        <div className="flex items-center justify-center mb-10">
            {[1, 2, 3].map((s, i) => (
                <React.Fragment key={s}>
                    {/* 连接线 */}
                    {i > 0 && (
                        <div className={`w-16 h-0.5 transition-colors duration-300 ${step >= s ? 'bg-white' : 'bg-slate-700'
                            }`} />
                    )}
                    {/* 节点 */}
                    <div className={`w-3 h-3 rounded-full transition-colors duration-300 ${step >= s ? 'bg-white shadow-[0_0_10px_rgba(255,255,255,0.5)]' : 'bg-slate-700'
                        }`} />
                </React.Fragment>
            ))}
        </div>
    );

    const renderStep1 = () => (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-white mb-2">您希望获取哪些论文？</h3>
                <p className="text-slate-400 text-sm">我们将根据您的偏好为您推荐最相关的研究成果</p>
            </div>

            <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                    研究偏好 <span className="text-red-400">*</span>
                </label>
                <textarea
                    value={formData.preferences}
                    onChange={e => setFormData({ ...formData, preferences: e.target.value })}
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-3 text-white h-32 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all resize-none"
                    placeholder="例如：我主要关注大语言模型在医疗领域的应用，特别是关于幻觉消除和知识库对齐的研究..."
                    required
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                    主要关注领域 <span className="text-red-400">*</span>
                </label>
                <CategorySelector
                    selectedCategories={formData.category}
                    onChange={(categories) => {
                        setFormData({
                            ...formData,
                            category: categories
                        });
                    }}
                />
            </div>

            <button
                onClick={() => setStep(2)}
                disabled={!formData.preferences || formData.category.length === 0}
                className="w-full mt-8 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-6 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
                下一步 <ArrowRight size={18} />
            </button>
        </div>
    );

    const renderStep2 = () => (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-white mb-2">您的特别关注？</h3>
                <p className="text-slate-400 text-sm">添加特定关键词、作者或机构，精准追踪前沿动态</p>
            </div>

            <TagInput
                label="关键词 (Keywords)"
                tags={formData.keywords}
                onChange={tags => setFormData({ ...formData, keywords: tags })}
                placeholder="输入关键词并回车..."
                addButtonText="添加关键词"
            />

            <TagInput
                label="关注作者 (Authors)"
                tags={formData.authors}
                onChange={tags => setFormData({ ...formData, authors: tags })}
                placeholder="输入作者姓名并回车..."
                addButtonText="添加作者"
            />

            <TagInput
                label="关注机构 (Institutions)"
                tags={formData.institutions}
                onChange={tags => setFormData({ ...formData, institutions: tags })}
                placeholder="输入机构名称并回车..."
                addButtonText="添加机构"
            />

            <div className="flex gap-4 mt-8">
                <button
                    onClick={() => setStep(3)}
                    className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium py-3 px-6 rounded-lg transition-all border border-slate-700"
                >
                    稍后设置
                </button>
                <button
                    onClick={() => setStep(3)}
                    className="flex-[2] bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-6 rounded-lg transition-all flex items-center justify-center gap-2"
                >
                    下一步 <ArrowRight size={18} />
                </button>
            </div>
        </div>
    );

    const renderStep3 = () => (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-white mb-2">您的研究现状？</h3>
                <p className="text-slate-400 text-sm">了解您的当前任务与目标，为您提供更贴合的建议</p>
            </div>

            <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">当前任务</label>
                <input
                    type="text"
                    value={formData.currentTask}
                    onChange={e => setFormData({ ...formData, currentTask: e.target.value })}
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                    placeholder="例如：正在撰写关于 RAG 的综述论文"
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">未来目标</label>
                <input
                    type="text"
                    value={formData.futureGoal}
                    onChange={e => setFormData({ ...formData, futureGoal: e.target.value })}
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                    placeholder="例如：发表一篇顶会论文"
                />
            </div>

            <div className="flex gap-4 mt-8">
                <button
                    onClick={handleUpdateProfile}
                    disabled={loading}
                    className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium py-3 px-6 rounded-lg transition-all border border-slate-700"
                >
                    稍后设置
                </button>
                <button
                    onClick={handleUpdateProfile}
                    disabled={loading}
                    className="flex-[2] bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-6 rounded-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                    {loading ? '保存中...' : '完成初始化'} <Check size={18} />
                </button>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-12">
            <div className="max-w-xl w-full bg-slate-900/50 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-sm">
                <ProgressBar />
                {step === 1 && renderStep1()}
                {step === 2 && renderStep2()}
                {step === 3 && renderStep3()}
            </div>
        </div>
    );
};
