import React, { useState, useEffect } from 'react';
import { Sparkles, Play, Save, AlertTriangle, X, Loader2, HelpCircle } from 'lucide-react';
import { WorkflowProgress } from './workflow/WorkflowProgress';
import { CategorySelector } from '../common/CategorySelector';
import { TagInput } from '../common/TagInput';
import { ToolsAPI, WorkflowAPI, UserAPI } from '../../services/api';
import type { UserProfile } from '../../types';
import { useTaskContext } from '../../contexts/TaskContext';
import type { StepProgress } from '../../types';

interface ManualReportPageProps {
    userProfile: UserProfile;
    onBack: () => void;
}

import { WORKFLOW_STEPS } from '../../constants/workflow';

const STEPS = WORKFLOW_STEPS;

// Helper function to transform steps for UI
const transformStepsForUI = (steps: StepProgress[]): StepProgress[] => {
    const crawlerStep = steps.find(s => s.name === 'run_crawler');
    const fetchStep = steps.find(s => s.name === 'fetch_details');
    const analyzeStep = steps.find(s => s.name === 'analyze_public_papers');
    const archiveStep = steps.find(s => s.name === 'archive_daily_papers');
    const filterStep = steps.find(s => s.name === 'personalized_filter');
    const reportStep = steps.find(s => s.name === 'generate_report');

    const newSteps: StepProgress[] = [];

    // 1. Merge Crawler & Fetch -> "获取新论文"
    let mergedCrawlerStatus: StepProgress['status'] = 'pending';
    let mergedCrawlerProgress = 0;
    let mergedCrawlerMessage = '';
    let mergedCrawlerDuration = 0;
    let fetchedCount = 0; // Track fetched count for next step

    if (crawlerStep || fetchStep) {
        // Default to crawler state if available
        if (crawlerStep) {
            mergedCrawlerStatus = crawlerStep.status;
            mergedCrawlerProgress = crawlerStep.progress / 2;
            mergedCrawlerMessage = crawlerStep.message || '正在检查更新...';
            mergedCrawlerDuration += (crawlerStep.duration_ms || 0);

            // [Fix] Extract paper count from message
            // Pattern: "捕获 6 篇论文"
            if (crawlerStep.status === 'completed' || crawlerStep.message?.includes('捕获')) {
                const match = crawlerStep.message?.match(/捕获\s*(\d+)\s*篇/);
                if (match) {
                    fetchedCount = parseInt(match[1], 10);
                    mergedCrawlerMessage = `总共获取${fetchedCount}篇论文`;
                } else if (crawlerStep.status === 'completed') {
                    mergedCrawlerMessage = '获取完成';
                }
            }
        }

        // Override/Update with fetch state
        if (fetchStep) {
            if (crawlerStep?.status === 'completed') {
                if (fetchStep.status === 'pending') {
                    mergedCrawlerStatus = 'running';
                    mergedCrawlerProgress = 50;
                    mergedCrawlerMessage = '准备获取详情...';
                } else if (fetchStep.status === 'running') {
                    mergedCrawlerStatus = 'running';
                    mergedCrawlerProgress = 50 + (fetchStep.progress / 2);
                    mergedCrawlerMessage = fetchStep.message || '正在获取详情...';
                } else if (fetchStep.status === 'completed') {
                    mergedCrawlerStatus = 'completed';
                    mergedCrawlerProgress = 100;
                    // Keep the count message if possible
                    if (fetchedCount > 0) {
                        mergedCrawlerMessage = `总共获取${fetchedCount}篇论文`;
                    } else {
                        mergedCrawlerMessage = '获取完成';
                    }
                } else if (fetchStep.status === 'failed') {
                    mergedCrawlerStatus = 'failed';
                    mergedCrawlerMessage = fetchStep.message || '获取详情失败';
                }
                mergedCrawlerDuration += (fetchStep.duration_ms || 0);
            } else if (crawlerStep?.status === 'failed') {
                mergedCrawlerStatus = 'failed';
                mergedCrawlerMessage = crawlerStep.message || '爬取失败';
            }
        }

        newSteps.push({
            name: 'run_crawler_merged',
            label: '获取新论文',
            status: mergedCrawlerStatus,
            progress: mergedCrawlerProgress,
            message: mergedCrawlerMessage,
            duration_ms: mergedCrawlerDuration
        });
    } else {
        // Initial state
        newSteps.push({ name: 'run_crawler_merged', label: '获取新论文', status: 'pending', progress: 0 });
    }

    // 2. Analyze Step -> "详情分析"
    // [Fix] Merge hidden "archive" step into "analyze" step
    let analyzeStatus = analyzeStep?.status || 'pending';
    let analyzeProgress = analyzeStep?.progress || 0;
    let analyzeMessage = analyzeStep?.message || '';
    let analyzeDuration = analyzeStep?.duration_ms || 0;

    // If archive is running, keep analyze as running (archiving)
    if (archiveStep?.status === 'running') {
        analyzeStatus = 'running';
        analyzeMessage = '正在归档数据...';
        analyzeProgress = 95; // Almost done
    } else if (analyzeStep) {
        // 【修复】从消息中提取真实的论文数，而不是使用 current/total（那是进度百分比！）
        if (analyzeStep.status === 'running' || analyzeStep.status === 'completed') {
            // 尝试从消息中提取论文数："正在归档 6 篇论文..." 或 "已归档 6 篇新论文"
            const match = analyzeStep.message?.match(/(\d+)\s*篇/);
            if (match) {
                const paperCount = parseInt(match[1], 10);
                if (analyzeStep.status === 'completed') {
                    analyzeMessage = `已经分析${paperCount}篇论文`;
                } else {
                    analyzeMessage = `正在分析，已处理${paperCount}篇论文`;
                }
            } else if (fetchedCount > 0) {
                // Fallback: 使用前一步骤获取的论文数
                if (analyzeStep.status === 'completed') {
                    analyzeMessage = `已经分析${fetchedCount}篇论文`;
                } else {
                    analyzeMessage = analyzeStep.message || '正在分析论文...';
                }
            } else {
                // 使用原始消息
                analyzeMessage = analyzeStep.message || (analyzeStep.status === 'completed' ? '分析完成' : '正在分析...');
            }
        }
    }

    // Only mark as completed if archive is also completed (or skipped/failed)
    if (analyzeStep?.status === 'completed' && archiveStep?.status === 'completed') {
        analyzeStatus = 'completed';
    } else if (analyzeStep?.status === 'completed' && (!archiveStep || archiveStep.status === 'pending')) {
        // If archive hasn't started yet but analyze is done, show as running/waiting
        analyzeStatus = 'running';
        analyzeMessage = '准备归档...';
    }

    newSteps.push({
        name: 'analyze_public_papers',
        label: '详情分析',
        status: analyzeStatus,
        progress: analyzeProgress,
        message: analyzeMessage,
        duration_ms: analyzeDuration
    });

    // 3. Filter Step -> "个性化筛选"
    let filterStatus = filterStep?.status || 'pending';
    let filterProgress = filterStep?.progress || 0;
    let filterMessage = filterStep?.message || '';
    let filterDuration = filterStep?.duration_ms || 0;

    if (filterStep) {
        // [Fix] Sanitize User ID & Extract Accepted Count
        if (filterStatus === 'completed') {
            const match = filterMessage?.match(/Accepted:\s*(\d+)/);
            if (match) {
                filterMessage = `已筛选${match[1]}篇高相关度论文`;
            } else {
                filterMessage = '个性化筛选完成';
            }
        } else if (filterStatus === 'running') {
            // Simplify running message
            filterMessage = '正在筛选论文';
        }
    }

    newSteps.push({
        name: 'personalized_filter',
        label: '个性化筛选',
        status: filterStatus,
        progress: filterProgress,
        message: filterMessage,
        duration_ms: filterDuration
    });

    // 4. Report Step -> "生成报告"
    if (reportStep) {
        const newReportStep = { ...reportStep, label: '生成报告' };

        // [Fix] Simplify running message
        if (newReportStep.status === 'running') {
            newReportStep.message = '正在生成报告';
        } else if (newReportStep.status === 'completed') {
            newReportStep.message = '已生成报告并发送至邮箱';
        }

        newSteps.push(newReportStep);
    } else {
        newSteps.push({ name: 'generate_report', label: '生成报告', status: 'pending', progress: 0 });
    }

    return newSteps;
};

export const ManualReportPage: React.FC<ManualReportPageProps> = ({ userProfile, onBack }) => {
    /**
     * 手动生成报告页面组件。
     * 
     * 功能：
     * 1. 提供自然语言输入框，允许用户描述想要阅读的论文。
     * 2. 集成 AI 智能填充功能，自动提取分类和作者。
     * 3. 提供手动管理分类和作者的界面。
     * 4. 显示预计消耗的光子数。
     * 5. 触发后端手动工作流，并实时显示进度。
     */

    // Input States (输入状态)
    const [naturalQuery, setNaturalQuery] = useState('');
    const [categories, setCategories] = useState<string[]>([]);
    const [authors, setAuthors] = useState<string[]>([]);

    // UI States (UI 状态)
    const [isAiLoading, setIsAiLoading] = useState(false);
    const [isStarting, setIsStarting] = useState(false); // Local state for API call duration
    const [showConfirm, setShowConfirm] = useState(false);

    // Workflow States (工作流状态)
    const { isGenerating, steps, startTask } = useTaskContext();
    const [error, setError] = useState<string | null>(null);

    // Transform steps for UI display
    const uiSteps = React.useMemo(() => transformStepsForUI(steps), [steps]);

    useEffect(() => {
        // Optional: Pre-fill logic (可选：预填充逻辑)
    }, []);

    /**
     * 处理 AI 智能填充。
     * 调用后端接口提取分类和作者，并自动填充到对应状态中。
     */
    const handleAiFill = async () => {
        if (!naturalQuery.trim()) return;

        setIsAiLoading(true);
        try {
            const result = await ToolsAPI.extractCategories(naturalQuery);
            if (result.categories) {
                // Replace categories (覆盖旧的分类)
                setCategories(result.categories);
            }
            if (result.authors) {
                // Replace authors (覆盖旧的作者)
                setAuthors(result.authors);
            }
        } catch (err) {
            console.error("AI Fill failed", err);
            // Optional: Show toast error
        } finally {
            setIsAiLoading(false);
        }
    };



    /**
     * 处理保存为默认设置。
     * 将当前配置更新到用户画像中。
     */
    const handleSaveAsDefault = async () => {
        if (!confirm("确定要将当前设置保存为默认偏好吗？这将覆盖您之前的设置。")) return;

        try {
            // Update profile logic here
            // Assuming we update focus categories and description
            await UserAPI.updateFocus({
                category: categories,
                description: naturalQuery,
                keywords: [], // Clear keywords as we use description
                authors: authors
            });
            alert("设置已保存！");
        } catch (err) {
            console.error("Save failed", err);
            alert("保存失败，请重试。");
        }
    };

    /**
     * 开始生成报告。
     * 1. 重置状态。
     * 2. 调用后端 manualTrigger 接口。
     * 3. 建立 SSE 连接监听进度。
     */
    const startGeneration = async () => {
        setError(null);
        setShowConfirm(false);
        setIsStarting(true);

        const initialSteps = STEPS.map(s => ({ ...s, status: 'pending', progress: 0 } as StepProgress));

        try {
            const { execution_id } = await WorkflowAPI.manualTrigger({
                user_id: userProfile.info.id || '', // Fix: use info.id
                natural_query: naturalQuery,
                categories: categories,
                authors: authors
            });

            if (execution_id) {
                startTask(execution_id, initialSteps);
            } else {
                setError("无法获取执行 ID");
            }
        } catch (err: any) {
            setError(err.message || "启动失败");
        } finally {
            setIsStarting(false);
        }
    };

    // Cost Estimation (成本估算)
    // Tiered pricing: 200 papers = 99 Photons, 201-300 = +50 Photons...
    // Just a static display for now as we don't know exact paper count before crawling
    const estimatedCost = "99+";

    return (
        <div className="flex h-full bg-slate-950 text-slate-200">
            {/* Left Panel: Input & Config */}
            <div className="w-2/3 p-8 border-r border-slate-800 overflow-y-auto">
                <div className="flex items-center justify-between mb-8">
                    <h1 className="text-2xl font-bold text-white">立即生成报告</h1>
                    <button onClick={onBack} className="text-slate-400 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </div>

                {/* Natural Language Input */}
                <div className="mb-8">
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        我想看什么论文？
                    </label>
                    <div className="relative">
                        <textarea
                            value={naturalQuery}
                            onChange={(e) => setNaturalQuery(e.target.value)}
                            placeholder="例如：我想看最近关于大模型微调的论文，特别是涉及 LoRA 的..."
                            className="w-full h-32 bg-slate-900 border border-slate-700 rounded-xl p-4 text-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all resize-none"
                        />
                        <button
                            onClick={handleAiFill}
                            disabled={isAiLoading || !naturalQuery.trim()}
                            className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isAiLoading ? <Loader2 className="animate-spin w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
                            AI 智能填充
                        </button>
                    </div>
                </div>

                {/* Categories */}
                <div className="mb-8">
                    <CategorySelector
                        selectedCategories={categories}
                        onChange={setCategories}
                    />
                </div>

                {/* Authors */}
                <div className="mb-8">
                    <TagInput
                        label="查询作者 (可选)"
                        tags={authors}
                        onChange={setAuthors}
                        placeholder="添加作者 (回车)..."
                        addButtonText="添加作者"
                    />
                </div>

                {/* Actions & Cost */}
                <div className="mt-12 pt-8 border-t border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="px-4 py-2 bg-slate-900 rounded-lg border border-slate-800 flex items-center gap-2 relative group cursor-help">
                            <span className="text-slate-400 text-sm">预计消耗:</span>
                            <span className="text-amber-400 font-bold">{estimatedCost} 光子</span>
                            <HelpCircle size={14} className="text-slate-600" />

                            {/* Cost Explanation Tooltip */}
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                                <h4 className="text-xs font-bold text-white mb-1">计费规则</h4>
                                <ul className="text-xs text-slate-400 space-y-1">
                                    <li>• 基础消耗: 99 光子 (200篇内论文)</li>
                                    <li>• 处理论文数在201-300篇之间: 149光子</li>
                                    <li>• 以此类推...</li>
                                </ul>
                                <div className="absolute bottom-[-4px] left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-800 border-r border-b border-slate-700 rotate-45"></div>
                            </div>
                        </div>
                        <button
                            onClick={handleSaveAsDefault}
                            className="flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-white transition-colors"
                        >
                            <Save size={18} />
                            <span className="text-sm">保存为默认设置</span>
                        </button>
                    </div>

                    <button
                        onClick={() => setShowConfirm(true)}
                        disabled={isGenerating || isStarting || categories.length === 0}
                        className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95"
                    >
                        {isGenerating || isStarting ? <Loader2 className="animate-spin" /> : <Play fill="currentColor" />}
                        立即生成今日报告
                    </button>
                </div>
            </div>

            {/* Right Panel: Progress */}
            <div className="w-1/3 bg-slate-900 border-l border-slate-800 flex flex-col">
                <div className="p-6 border-b border-slate-800">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        任务进度
                        {isGenerating && <span className="flex h-2 w-2 rounded-full bg-green-500 animate-pulse" />}
                    </h2>
                </div>
                <div className="flex-1 overflow-hidden">
                    <WorkflowProgress steps={uiSteps} />
                </div>
                {error && (
                    <div className="p-4 m-4 bg-red-900/20 border border-red-900/50 rounded-lg text-red-400 text-sm flex items-start gap-2">
                        <AlertTriangle className="shrink-0 w-4 h-4 mt-0.5" />
                        {error}
                    </div>
                )}
            </div>
            // ...

            {/* Confirm Modal */}
            {showConfirm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="bg-slate-900 border border-slate-700 p-6 rounded-2xl max-w-md w-full shadow-2xl">
                        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                            <AlertTriangle className="text-amber-500" />
                            确认生成？
                        </h3>
                        <p className="text-slate-400 mb-6">
                            这将执行新的分析流程，可能会覆盖您今日已生成的部分论文数据。
                            <br /><br />
                            预计消耗光子: <span className="text-amber-400 font-bold">{estimatedCost}</span>
                        </p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setShowConfirm(false)}
                                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={startGeneration}
                                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium"
                            >
                                确认并支付
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
