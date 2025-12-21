import React, { useEffect, useState, useRef } from 'react';
import { WorkflowAPI } from '../../services/api';
import { X, CheckCircle, Loader2, AlertCircle, ChevronRight } from 'lucide-react';
import { WorkflowProgress } from './workflow/WorkflowProgress';
import type { StepProgress } from '../../types';

/**
 * 报告生成弹窗组件的参数接口
 */
interface ReportGenerationModalProps {
    isOpen: boolean;
    onClose: () => void;
    userId: string;
    onComplete?: () => void;
    /** 用户邮箱，用于判断完成提示显示内容 */
    userEmail?: string;
}



import { WORKFLOW_STEPS } from '../../constants/workflow';

const STEPS = WORKFLOW_STEPS;

/**
 * 报告生成弹窗组件
 * 
 * 功能：显示工作流执行进度，支持实时更新步骤状态
 * 
 * 【重要修改】2024-12-21：
 * 由于 Bohrium 容器环境的反向代理导致 SSE 连接不稳定，
 * 将原来的 SSE 长连接改为定时轮询模式。
 */
export const ReportGenerationModal: React.FC<ReportGenerationModalProps> = ({ isOpen, onClose, userId, onComplete, userEmail }) => {
    const [steps, setSteps] = useState<StepProgress[]>(
        STEPS.map(s => ({ ...s, status: 'pending', progress: 0 }))
    );
    const [error, setError] = useState<string | null>(null);
    const [isCompleted, setIsCompleted] = useState(false);
    
    // 【轮询模式】替代原有的 SSE 相关 refs
    const pollingTimeoutRef = useRef<number | null>(null);
    const isPollingRef = useRef<boolean>(false);
    const failCountRef = useRef<number>(0);
    
    const hasTriggeredRef = useRef(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    // 轮询配置
    const POLL_INTERVAL = 2000;         // 轮询间隔：2 秒
    const MAX_FAIL_COUNT = 5;           // 最大连续失败次数
    const BACKOFF_MULTIPLIER = 1.5;     // 失败后延迟倍数

    // Auto-scroll to bottom when steps update
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [steps]);

    useEffect(() => {
        if (isOpen && !hasTriggeredRef.current) {
            startGeneration();
        }

        return () => {
            stopPolling();
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen]);

    /**
     * 停止轮询
     * 
     * 功能：清理轮询定时器，重置状态
     */
    const stopPolling = () => {
        console.log("[轮询] 停止轮询");
        isPollingRef.current = false;
        
        if (pollingTimeoutRef.current) {
            clearTimeout(pollingTimeoutRef.current);
            pollingTimeoutRef.current = null;
        }
        
        failCountRef.current = 0;
    };

    // [NEW] Refs for persistent counts
    const countsRef = useRef({ fetched: 0, analyzed: 0, filtered: 0 });

    const updateSteps = (backendSteps: any[]) => {
        setSteps(prevSteps => {
            const newSteps = [...prevSteps];
            let hasRunningStep = false;
            let lastCompletedIndex = -1;

            // Helper to find backend step by name
            const findBackendStep = (name: string) => backendSteps.find((s: any) => s.name === name);

            // [Logic] Archive Step Merging
            // We need to check 'archive_daily_papers' status to influence 'analyze_public_papers'
            const archiveStep = findBackendStep('archive_daily_papers');
            const analyzeStep = findBackendStep('analyze_public_papers');

            // 1. Map backend steps to UI steps & Extract Counts
            newSteps.forEach((uiStep, index) => {
                const bStep = findBackendStep(uiStep.name);

                // Special handling for analyze step to merge archive status
                if (uiStep.name === 'analyze_public_papers') {
                    // Default to backend status or keep current if not found
                    let status = bStep?.status || uiStep.status;
                    let message = bStep?.message || uiStep.message;
                    let progress = uiStep.progress;
                    let duration = bStep?.duration_ms || uiStep.duration_ms;

                    // If analyze is done (or not started), but archive is running/pending, keep analyze "running"
                    if (archiveStep) {
                        if (archiveStep.status === 'running') {
                            status = 'running';
                            message = '正在归档数据...';
                            // If analyze was already done, show 100% or keep current
                            if (bStep?.status === 'completed') progress = 100;
                        } else if (archiveStep.status === 'pending' && bStep?.status === 'completed') {
                            // Analyze done, waiting for archive
                            status = 'running';
                            message = '准备归档...';
                            progress = 100;
                        } else if (archiveStep.status === 'completed' && bStep?.status === 'completed') {
                            status = 'completed';
                        }
                    }

                    // Update UI Step
                    newSteps[index] = {
                        ...uiStep,
                        status,
                        message,
                        progress,
                        duration_ms: duration
                    };

                    // Extract Counts for Analyze
                    // 【修复】从消息中提取真实论文数，而不是使用 progress.current（那是进度百分比！）
                    const paperMatch = bStep?.message?.match(/(\d+)\s*篇/);
                    if (paperMatch) {
                        const val = parseInt(paperMatch[1], 10);
                        if (val > countsRef.current.analyzed) countsRef.current.analyzed = val;
                    }

                } else if (bStep) {
                    // Normal mapping for other steps
                    const currentStep = { ...newSteps[index] };

                    // [Optimistic] Prevent backtracking for first step
                    // If UI is running and backend says pending, ignore backend
                    if (index === 0 && currentStep.status === 'running' && bStep.status === 'pending') {
                        // Keep running, do nothing
                    } else {
                        currentStep.status = bStep.status;
                    }

                    currentStep.duration_ms = bStep.duration_ms;

                    // [Logic] Extract & Persist Counts
                    if (bStep.name === 'run_crawler' || bStep.name === 'fetch_details') {
                        const match = bStep.message?.match(/(?:捕获|获取|total|Fetched).*?(\d+)/i);
                        if (match) countsRef.current.fetched = parseInt(match[1]);
                    } else if (bStep.name === 'personalized_filter') {
                        const match = bStep.message?.match(/(?:Accepted|筛选|selected).*?(\d+)/i);
                        if (match) countsRef.current.filtered = parseInt(match[1]);
                    }

                    // [Logic] Progress & Message
                    if (bStep.progress) {
                        const { current, total, message } = bStep.progress;
                        if (total > 0) {
                            currentStep.progress = Math.round((current / total) * 100);
                        }
                        if (message) currentStep.message = message;
                    } else if (bStep.status === 'completed') {
                        currentStep.progress = 100;
                        // [Logic] Override completion message with counts
                        if (bStep.name === 'run_crawler' || bStep.name === 'fetch_details') {
                            currentStep.message = countsRef.current.fetched > 0
                                ? `共获取 ${countsRef.current.fetched} 篇论文`
                                : '获取完成';
                        } else if (bStep.name === 'personalized_filter') {
                            currentStep.message = countsRef.current.filtered > 0
                                ? `已筛选 ${countsRef.current.filtered} 篇高相关论文`
                                : '筛选完成';
                        } else {
                            currentStep.message = "完成";
                        }
                    } else if (bStep.status === 'running') {
                        if (!currentStep.message) currentStep.message = "正在执行...";
                    }

                    newSteps[index] = currentStep;
                }
            });

            // Re-apply Analyze Message Override (outside loop to ensure it uses latest status)
            const analyzeUiStep = newSteps.find(s => s.name === 'analyze_public_papers');
            if (analyzeUiStep && analyzeUiStep.status === 'completed') {
                analyzeUiStep.message = countsRef.current.analyzed > 0
                    ? `已分析 ${countsRef.current.analyzed} 篇论文`
                    : '分析完成';
            }

            // Check for running steps
            hasRunningStep = newSteps.some(s => s.status === 'running');

            // 2. [Optimistic] Gap Filling Logic
            if (!hasRunningStep && !isCompleted) {
                // Find last completed step
                for (let i = 0; i < newSteps.length; i++) {
                    if (newSteps[i].status === 'completed') {
                        lastCompletedIndex = i;
                    }
                }

                // If we have a completed step, and there is a next step
                if (lastCompletedIndex !== -1 && lastCompletedIndex < newSteps.length - 1) {
                    const nextStepIndex = lastCompletedIndex + 1;
                    const nextStep = newSteps[nextStepIndex];

                    // Only if it's pending (don't overwrite failed)
                    if (nextStep.status === 'pending') {
                        newSteps[nextStepIndex] = {
                            ...nextStep,
                            status: 'running',
                            message: '准备中...',
                            progress: 0
                        };
                    }
                }
            }

            return newSteps;
        });
    };

    /**
     * 处理轮询错误
     * 
     * 功能：设置错误状态，停止轮询，更新步骤状态
     * 
     * Args:
     *   errorMessage: 错误消息
     */
    const handlePollingError = (errorMessage: string) => {
        console.error("[轮询] 错误:", errorMessage);
        setError(errorMessage);
        stopPolling();

        // 强制更新 running/pending 步骤为 failed
        setSteps(prevSteps => prevSteps.map(step => {
            if (step.status === 'running' || step.status === 'pending') {
                return { ...step, status: 'failed', message: '任务中断' };
            }
            return step;
        }));
    };

    /**
     * 启动轮询
     * 
     * 功能：开始定时请求后端进度端点
     * 
     * Args:
     *   executionId: 工作流执行 ID
     */
    const startPolling = (executionId: string) => {
        stopPolling(); // 先停止现有轮询
        
        console.log(`[轮询] 开始轮询 execution: ${executionId}`);
        isPollingRef.current = true;
        failCountRef.current = 0;
        
        // 立即执行第一次轮询
        pollProgress(executionId);
    };

    /**
     * 执行单次轮询
     * 
     * 功能：请求后端进度端点，处理响应，安排下一次轮询
     * 
     * Args:
     *   executionId: 工作流执行 ID
     */
    const pollProgress = async (executionId: string) => {
        // 检查是否应该继续轮询
        if (!isPollingRef.current) {
            console.log("[轮询] 轮询已停止，退出");
            return;
        }
        
        try {
            const url = `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/workflow/progress/${executionId}`;
            const response = await fetch(url, { credentials: 'include' });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // 重置失败计数
            failCountRef.current = 0;
            
            // 更新步骤状态
            if (data.steps) {
                updateSteps(data.steps);
            }
            
            // 检查任务是否结束
            if (data.status === 'completed') {
                console.log("[轮询] 任务成功完成");
                setIsCompleted(true);
                stopPolling();
                if (onComplete) onComplete();
                return;
            } else if (data.status === 'failed') {
                console.log("[轮询] 任务执行失败");
                handlePollingError("任务执行失败");
                return;
            } else if (data.status === 'stopped') {
                console.log("[轮询] 任务提前终止");
                setIsCompleted(true);
                stopPolling();
                setSteps(prevSteps => prevSteps.map(step => {
                    if (step.status === 'running' || step.status === 'pending') {
                        return { ...step, status: 'completed', message: '已停止' };
                    }
                    return step;
                }));
                if (onComplete) onComplete();
                return;
            }
            
            // 任务仍在进行中，安排下一次轮询
            pollingTimeoutRef.current = window.setTimeout(() => pollProgress(executionId), POLL_INTERVAL);
            
        } catch (error) {
            console.error("[轮询] 请求失败:", error);
            failCountRef.current++;
            
            if (failCountRef.current >= MAX_FAIL_COUNT) {
                // 连续失败次数过多，标记任务失败
                console.error(`[轮询] 连续失败 ${MAX_FAIL_COUNT} 次，任务标记为失败`);
                handlePollingError("连接中断，任务可能已停止");
                return;
            }
            
            // 计算退避延迟
            const backoffDelay = POLL_INTERVAL * Math.pow(BACKOFF_MULTIPLIER, failCountRef.current);
            console.log(`[轮询] 将在 ${Math.round(backoffDelay)}ms 后重试 (失败 ${failCountRef.current}/${MAX_FAIL_COUNT})`);
            
            pollingTimeoutRef.current = window.setTimeout(() => pollProgress(executionId), backoffDelay);
        }
    };

    /**
     * 开始生成报告
     * 
     * 功能：触发工作流执行，启动轮询
     */
    const startGeneration = async () => {
        hasTriggeredRef.current = true;
        setError(null);
        setIsCompleted(false);
        // 乐观更新：立即将第一步设为 running
        setSteps(STEPS.map((s, i) => ({
            ...s,
            status: i === 0 ? 'running' : 'pending',
            progress: 0,
            message: i === 0 ? '正在连接...' : undefined
        })));

        // 重置计数
        countsRef.current = { fetched: 0, analyzed: 0, filtered: 0 };

        try {
            const { execution_id } = await WorkflowAPI.triggerDaily(userId);

            if (execution_id) {
                startPolling(execution_id);
            } else {
                setError("无法获取执行 ID");
            }
        } catch (err: any) {
            setError(err.message || "启动失败");
        }
    };

    /**
     * 关闭弹窗
     * 
     * 功能：停止轮询，重置状态，关闭弹窗
     */
    const handleClose = () => {
        stopPolling();
        hasTriggeredRef.current = false;
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm transition-all duration-300">
            <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-5xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in duration-300 border border-gray-100 dark:border-gray-800">

                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-white/50 dark:bg-gray-900/50 backdrop-blur-md sticky top-0 z-10">
                    <div>
                        <h2 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                            {isCompleted ? (
                                <>
                                    <CheckCircle className="text-green-500 w-10 h-10" />
                                    <span>生成完成</span>
                                </>
                            ) : error ? (
                                <>
                                    <AlertCircle className="text-red-500 w-10 h-10" />
                                    <span>生成失败</span>
                                </>
                            ) : (
                                <>
                                    <Loader2 className="animate-spin text-blue-600 w-10 h-10" />
                                    <span>正在生成报告...</span>
                                </>
                            )}
                        </h2>
                        <p className="text-lg text-gray-500 dark:text-gray-400 mt-2">
                            {isCompleted 
                                ? (userEmail?.trim() ? "您的日报已发送至邮箱" : "报告已生成") 
                                : "请稍候，正在处理您的订阅内容"}
                        </p>
                    </div>
                    <button
                        onClick={handleClose}
                        className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Body - Vertical Stepper */}
                <WorkflowProgress steps={steps} />

                {/* Footer */}
                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
                    {error ? (
                        <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl flex items-start gap-3 mb-4">
                            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                            <p className="text-sm font-medium">{error}</p>
                        </div>
                    ) : null}

                    <div className="flex justify-end gap-3">
                        {isCompleted ? (
                            <button
                                onClick={handleClose}
                                className="px-6 py-2.5 bg-gray-900 hover:bg-gray-800 dark:bg-white dark:hover:bg-gray-100 text-white dark:text-gray-900 rounded-xl transition-all shadow-lg hover:shadow-xl font-medium flex items-center gap-2"
                            >
                                <span>查看报告</span>
                                <ChevronRight size={16} />
                            </button>
                        ) : (
                            <button
                                onClick={handleClose}
                                className="px-6 py-2.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 font-medium transition-colors"
                            >
                                后台运行
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
