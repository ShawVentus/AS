import React, { useState, useEffect } from 'react';
import { supabase } from '../../services/supabase';
import { UserAPI, PaymentAPI, PRICE_TIERS } from '../../services/api';
import type { UserProfile } from '../../types/user';
import { useToast } from '../../contexts/ToastContext';
import { Avatar } from '../common/Avatar';
import { TagInput } from '../common/TagInput';
import { CategorySelector } from '../common/CategorySelector';
import { ArrowLeft, Lightbulb, Save, LogOut, User, Plus, MoreVertical, Edit, Trash2, Coins, Loader2, Star, Flame } from 'lucide-react';

interface SettingsProps {
    userProfile: UserProfile;
    onUpdate: () => void;
    onBack: () => void;
    onNavigate?: (view: string) => void;
}

export const Settings: React.FC<SettingsProps> = ({ userProfile, onUpdate, onBack }) => {
    const { showToast } = useToast();

    const [loading, setLoading] = useState(false);
    
    // 购买状态（新增）
    const [purchasing, setPurchasing] = useState<string | null>(null);

    // Preferences 弹窗状态
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingIndex, setEditingIndex] = useState<number | null>(null);
    const [dialogValue, setDialogValue] = useState('');
    const [menuOpen, setMenuOpen] = useState<number | null>(null);

    // 确认对话框状态
    const [confirmDialog, setConfirmDialog] = useState<{
        open: boolean;
        title: string;
        message: string;
        onConfirm: () => void;
    }>({ open: false, title: '', message: '', onConfirm: () => { } });

    const [formData, setFormData] = useState({
        nickname: '',
        avatar: '',
        role: '',
        stage: '',
        preferences: [] as string[],  // 改为数组
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
                preferences: userProfile.context?.preferences || [],  // 默认空数组
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
            showToast('保存成功', 'success');
            onUpdate();
        } catch (error) {
            console.error('Error updating settings:', error);
            showToast('保存失败', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleAddPreference = () => {
        setEditingIndex(null);
        setDialogValue('');
        setDialogOpen(true);
        setMenuOpen(null);
    };

    const handleEditPreference = (index: number) => {
        setEditingIndex(index);
        setDialogValue(formData.preferences[index]);
        setDialogOpen(true);
        setMenuOpen(null);
    };

    const handleDeletePreference = (index: number) => {
        setConfirmDialog({
            open: true,
            title: '删除研究偏好',
            message: '确定要删除这条研究偏好吗？',
            onConfirm: () => {
                const newPreferences = formData.preferences.filter((_, i) => i !== index);
                setFormData({ ...formData, preferences: newPreferences });
                setMenuOpen(null);
                setConfirmDialog({ ...confirmDialog, open: false });
            }
        });
    };

    const handleDeleteAll = () => {
        setConfirmDialog({
            open: true,
            title: '删除所有偏好',
            message: `确定要删除所有 ${formData.preferences.length} 条研究偏好吗？此操作不可恢复。`,
            onConfirm: () => {
                setFormData({ ...formData, preferences: [] });
                setConfirmDialog({ ...confirmDialog, open: false });
            }
        });
    };

    const handleDialogSubmit = () => {
        const trimmed = dialogValue.trim();
        if (!trimmed) {
            showToast('研究偏好不能为空', 'warning');
            return;
        }

        if (trimmed.length > 200) {
            showToast('单条偏好最多200字符', 'warning');
            return;
        }

        if (editingIndex !== null) {
            // 编辑模式
            const newPreferences = [...formData.preferences];
            newPreferences[editingIndex] = trimmed;
            setFormData({ ...formData, preferences: newPreferences });
        } else {
            // 新增模式
            if (formData.preferences.length >= 10) {
                showToast('最多只能添加10条研究偏好', 'warning');
                return;
            }
            setFormData({ ...formData, preferences: [...formData.preferences, trimmed] });
        }

        setDialogOpen(false);
        setDialogValue('');
        setEditingIndex(null);
    };

    const handleLogout = async () => {
        await supabase.auth.signOut();
        window.location.reload();
    };

    return (
        <div className="p-6 max-w-6xl mx-auto space-y-4 pb-20 animate-in fade-in">
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
            <section className="bg-slate-900/50 rounded-xl p-5 border border-slate-800 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-4 text-slate-400">
                    <User size={20} />
                    <h2 className="text-lg font-semibold text-white">基础设置</h2>
                </div>
                <div className="flex items-start gap-6">
                    {/* 左侧：头像上传 */}
                    {/* 左侧：头像上传 */}
                    <div className="flex flex-col items-center gap-3 pt-2 pl-2">
                        <div className="relative group cursor-pointer w-20 h-20">
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
                                        showToast('头像上传成功，请点击保存以应用更改', 'success');
                                    } catch (error: any) {
                                        console.error('Error uploading avatar:', error);
                                        showToast(`头像上传失败: ${error.message || '请确保您已登录且网络正常'}`, 'error');
                                    } finally {
                                        setLoading(false);
                                    }
                                }}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10 rounded-full"
                            />
                            {formData.avatar ? (
                                <img src={formData.avatar} alt="Avatar" className="w-full h-full rounded-full object-cover border-4 border-slate-800 shadow-lg group-hover:opacity-75 transition-opacity" />
                            ) : (
                                <div className="w-full h-full group-hover:opacity-75 transition-opacity">
                                    <Avatar name={formData.nickname} size="xl" className="!w-full !h-full !text-3xl" />
                                </div>
                            )}
                            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                                <span className="bg-black/50 text-white text-xs px-2 py-1 rounded backdrop-blur-sm">更换头像</span>
                            </div>
                        </div>
                        <span className="text-xs text-slate-500">点击头像更换</span>
                    </div>

                    {/* 右侧：昵称、邮箱、邮件推送 */}
                    <div className="flex-1 space-y-3 max-w-md">
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

                        <div className="flex items-center justify-between">
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
            </section>

            {/* 账户额度（新增） - 添加 id 用于页面内定位 */}
            <section id="payment" className="bg-slate-900/50 rounded-xl p-5 border border-slate-800 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-4 text-amber-400">
                    <Coins size={20} />
                    <h2 className="text-lg font-semibold text-white">账户额度</h2>
                </div>

                {/* 当前余额显示 */}
                <div className="mb-6">
                    <span className="text-slate-400 text-sm">当前剩余次数：</span>
                    <span className="ml-2 inline-flex items-center px-3 py-1 bg-green-500/20 text-green-400 rounded-full font-semibold">
                        {userProfile?.info?.remaining_quota ?? 0} 次
                    </span>
                </div>

                {/* 价格卡片 */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {PRICE_TIERS.map((tier) => (
                        <div
                            key={tier.name}
                            className={`relative bg-slate-800/50 rounded-xl p-5 border transition-all hover:border-blue-500 ${
                                tier.recommended ? 'border-yellow-500/50' : tier.hot ? 'border-orange-500/50' : 'border-slate-700'
                            }`}
                        >
                            {/* 标签 */}
                            {tier.recommended && (
                                <div className="absolute -top-2 left-4 flex items-center gap-1 px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                                    <Star size={12} /> 推荐
                                </div>
                            )}
                            {tier.hot && (
                                <div className="absolute -top-2 left-4 flex items-center gap-1 px-2 py-0.5 bg-orange-500/20 text-orange-400 text-xs rounded-full">
                                    <Flame size={12} /> 超值
                                </div>
                            )}

                            {/* 档位名称 */}
                            <h3 className="text-white font-semibold mb-3 mt-1">{tier.name}</h3>

                            {/* 价格 */}
                            <div className="text-2xl font-bold text-blue-400 mb-1">
                                💎 {tier.eventValue} 光子
                            </div>

                            {/* 获得次数 */}
                            <div className="text-slate-400 text-sm mb-3">
                                获得 <span className="text-white font-semibold">{tier.quotaAmount}</span> 次
                            </div>

                            {/* 折扣标签 */}
                            {tier.discount && (
                                <div className="mb-3">
                                    <span className="inline-block px-2 py-0.5 bg-green-500 text-white text-xs font-medium rounded-full">
                                        {tier.discount}
                                    </span>
                                </div>
                            )}

                            {/* 购买按钮 */}
                            <button
                                onClick={async () => {
                                    if (purchasing) return;
                                    setPurchasing(tier.name);
                                    try {
                                        const result = await PaymentAPI.consume({
                                            eventValue: tier.eventValue,
                                            quotaAmount: tier.quotaAmount
                                        });
                                        if (result.success) {
                                            showToast(`购买成功，已获得 ${tier.quotaAmount} 次生成额度`, 'success');
                                            // 调用 onUpdate 刷新用户数据（优化：避免强制刷新整个页面）
                                            onUpdate();
                                        } else {
                                            showToast(result.message, 'error');
                                        }
                                    } catch (error: unknown) {
                                        const errorMessage = error instanceof Error ? error.message : '购买失败，请稍后重试';
                                        showToast(errorMessage, 'error');
                                    } finally {
                                        setPurchasing(null);
                                    }
                                }}
                                disabled={purchasing !== null}
                                className={`w-full py-2 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
                                    purchasing === tier.name
                                        ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                                        : 'bg-blue-600 hover:bg-blue-500 text-white'
                                }`}
                            >
                                {purchasing === tier.name ? (
                                    <>
                                        <Loader2 size={16} className="animate-spin" />
                                        购买中...
                                    </>
                                ) : (
                                    '立即购买'
                                )}
                            </button>
                        </div>
                    ))}
                </div>
            </section>

            {/* 研究偏好设置 - 重构为列表+弹窗模式 */}
            <section className="bg-slate-900/50 rounded-xl p-5 border border-slate-800 backdrop-blur-sm">
                {/* 顶部按钮栏 */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2 text-purple-400">
                        <Lightbulb size={20} />
                        <h2 className="text-lg font-semibold text-white">研究偏好设置</h2>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleAddPreference}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
                        >
                            <Plus size={16} />
                            添加偏好
                        </button>
                        {formData.preferences.length > 0 && (
                            <button
                                onClick={handleDeleteAll}
                                className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors text-sm"
                            >
                                <Trash2 size={16} />
                                删除所有偏好
                            </button>
                        )}
                    </div>
                </div>

                {/* Preferences 列表 */}
                <div className="space-y-2">
                    {formData.preferences.length === 0 ? (
                        <div className="text-center py-8 text-slate-500">
                            <Lightbulb size={32} className="mx-auto mb-2 opacity-50" />
                            <p>还没有设置研究偏好</p>
                            <p className="text-xs mt-1">点击 "添加偏好" 按钮添加你的第一条偏好</p>
                        </div>
                    ) : (
                        formData.preferences.map((pref, index) => (
                            <div
                                key={index}
                                className="group relative bg-slate-800/50 rounded-lg px-4 pt-3 pb-2 border border-slate-700 hover:border-slate-600 transition-colors"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <p className="text-slate-200 text-sm flex-1 leading-relaxed pr-8">
                                        {pref}
                                    </p>

                                    {/* 三点菜单 */}
                                    <div className="relative">
                                        <button
                                            onClick={() => setMenuOpen(menuOpen === index ? null : index)}
                                            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-700 transition-colors"
                                        >
                                            <MoreVertical size={18} />
                                        </button>

                                        {menuOpen === index && (
                                            <>
                                                {/* 点击外部关闭菜单 */}
                                                <div
                                                    className="fixed inset-0 z-10"
                                                    onClick={() => setMenuOpen(null)}
                                                />
                                                {/* 下拉菜单 */}
                                                <div className="absolute right-0 top-8 z-20 bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1 min-w-[120px]">
                                                    <button
                                                        onClick={() => handleEditPreference(index)}
                                                        className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                                                    >
                                                        <Edit size={14} />
                                                        Edit
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeletePreference(index)}
                                                        className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                                                    >
                                                        <Trash2 size={14} />
                                                        Delete
                                                    </button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                <div className="mt-4 space-y-2">
                    <p className="text-xs text-slate-500">
                        💡 <strong>示例</strong>：「我想找强化学习相关的文章」、「关注医疗AI应用」
                    </p>
                    <p className="text-xs text-slate-500">
                        ⚠️ <strong>限制</strong>：最多10条，每条最多200字符
                    </p>
                    <p className="text-xs text-yellow-500">
                        🔔 <strong>重要</strong>：未设置偏好将无法生成每日报告，添加后请点击页面右上角保存
                    </p>
                </div>
            </section>



            {/* Focus Areas */}
            <section className="bg-slate-900/50 rounded-xl p-5 border border-slate-800 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-4 text-indigo-400">
                    <Lightbulb size={20} />
                    <h2 className="text-lg font-semibold text-white">关注什么</h2>
                </div>

                <div className="space-y-6">
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
                    {/* <TagInput
                        label="关注机构 (Institutions)"
                        tags={formData.institutions}
                        onChange={tags => setFormData({ ...formData, institutions: tags })}
                        placeholder="输入机构名称并回车..."
                        addButtonText="添加机构"
                    /> */}
                </div>
            </section>

            {/* 弹窗对话框 */}
            {dialogOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-slate-900 rounded-xl border border-slate-700 shadow-2xl w-full max-w-2xl animate-in zoom-in-95">
                        {/* 对话框头部 */}
                        <div className="p-6 border-b border-slate-800">
                            <h3 className="text-xl font-semibold text-white">
                                {editingIndex !== null ? '编辑研究偏好' : '添加研究偏好'}
                            </h3>
                            <p className="text-sm text-slate-400 mt-1">
                                描述你的研究兴趣和需求（最多200字符）
                            </p>
                        </div>

                        {/* 对话框内容 */}
                        <div className="p-6">
                            <textarea
                                value={dialogValue}
                                onChange={(e) => setDialogValue(e.target.value)}
                                placeholder='例如："我想找强化学习相关的文章"'
                                className="w-full h-40 bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all resize-none"
                                autoFocus
                                maxLength={200}
                            />
                            <div className="mt-2 text-right text-xs text-slate-500">
                                {dialogValue.length} / 200 字符
                            </div>
                        </div>

                        {/* 对话框底部按钮 */}
                        <div className="p-6 border-t border-slate-800 flex justify-end gap-3">
                            <button
                                onClick={() => {
                                    setDialogOpen(false);
                                    setDialogValue('');
                                    setEditingIndex(null);
                                }}
                                className="px-6 py-2 text-slate-300 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDialogSubmit}
                                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                            >
                                {editingIndex !== null ? 'Save' : 'Submit'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* 确认对话框 */}
            {confirmDialog.open && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
                    <div className="bg-slate-900 rounded-xl border border-slate-700 shadow-2xl w-full max-w-md animate-in zoom-in-95">
                        {/* 对话框内容 */}
                        <div className="p-6">
                            <div className="flex items-start gap-4">
                                {/* 警告图标 */}
                                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center">
                                    <Trash2 size={24} className="text-red-400" />
                                </div>

                                {/* 文本内容 */}
                                <div className="flex-1">
                                    <h3 className="text-lg font-semibold text-white mb-2">
                                        {confirmDialog.title}
                                    </h3>
                                    <p className="text-sm text-slate-400">
                                        {confirmDialog.message}
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* 对话框底部按钮 */}
                        <div className="p-6 pt-0 flex justify-end gap-3">
                            <button
                                onClick={() => setConfirmDialog({ ...confirmDialog, open: false })}
                                className="px-6 py-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={confirmDialog.onConfirm}
                                className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                            >
                                确定删除
                            </button>
                        </div>
                    </div>
                </div>
            )}


            {/* 退出登录 */}
            <section className="bg-slate-900/50 rounded-xl p-5 border border-slate-800 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-semibold text-white mb-1">退出登录</h2>
                        <p className="text-sm text-slate-500">登出当前账户</p>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 bg-red-600/10 hover:bg-red-600/20 text-red-400 font-medium py-2 px-6 rounded-lg border border-red-600/30 hover:border-red-600/50 transition-all"
                    >
                        <LogOut size={16} />
                        退出登录
                    </button>
                </div>
            </section>
        </div>
    );
}
