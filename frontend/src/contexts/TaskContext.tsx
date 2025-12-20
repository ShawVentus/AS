import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from './ToastContext';
import { WORKFLOW_STEP_LABELS } from '../constants/workflow';
import { WorkflowAPI } from '../services/api';
import type { StepProgress } from '../types';


interface TaskContextType {
    isGenerating: boolean;
    executionId: string | null;
    steps: StepProgress[];
    startTask: (executionId: string, initialSteps: StepProgress[]) => void;
    stopTask: () => void;
    registerNavigation: (fn: (view: string, data?: any) => void) => void;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

/**
 * 全局任务上下文组件
 * 
 * 功能：
 * 1. 管理后台任务状态 (executionId, isGenerating, steps)。
 * 2. 负责 SSE 连接的建立、监听和断开。
 * 3. 任务完成或失败时触发全局 Toast 通知。
 * 4. 状态持久化到 localStorage，防止页面刷新丢失任务。
 */
export const TaskProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isGenerating, setIsGenerating] = useState(false);
    const [executionId, setExecutionId] = useState<string | null>(null);
    const [steps, setSteps] = useState<StepProgress[]>([]);
    const eventSourceRef = useRef<EventSource | null>(null);
    const navigationRef = useRef<((view: string, data?: any) => void) | null>(null);
    const heartbeatCheckerRef = useRef<number | null>(null);
    const initialTimeoutRef = useRef<number | null>(null);
    const completedRef = useRef<boolean>(false);
    const { showToast } = useToast();
    const queryClient = useQueryClient();

    // 从 localStorage 恢复状态 (Removed, moved to bottom)
    // useEffect(() => {
    //     const storedId = localStorage.getItem('current_manual_execution_id');
    //     if (storedId) {
    //         console.log("Restoring task from localStorage:", storedId);
    //         setExecutionId(storedId);
    //         setIsGenerating(true);
    //         // 恢复时，steps 可能为空，需要通过 SSE 或 API 获取最新状态
    //         // 这里我们依赖 SSE 连接后收到的第一条消息来更新 steps
    //     }
    // }, []);

    // 监听 executionId 变化，管理 SSE 连接
    useEffect(() => {
        if (executionId && isGenerating) {
            connectToSSE(executionId);
        } else {
            cleanupSSE();
        }

        return () => {
            cleanupSSE();
        };
    }, [executionId, isGenerating]);

    const cleanupSSE = () => {
        if (eventSourceRef.current) {
            console.log("Closing SSE connection");
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }

        // 清理心跳检查定时器
        if (heartbeatCheckerRef.current) {
            clearInterval(heartbeatCheckerRef.current);
            heartbeatCheckerRef.current = null;
        }

        // 【新增】清理初始超时设置
        initialTimeoutRef.current = null;
    };

    const connectToSSE = (id: string) => {
        if (eventSourceRef.current?.url.includes(id)) return; // 避免重复连接

        console.log("Connecting to SSE for execution:", id);
        const url = `${import.meta.env.VITE_API_BASE_URL || '/api'}/workflow/progress-stream/${id}`;
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        // 【新增】心跳超时检测
        let lastMessageTime = Date.now();
        let hasReceivedFirstMessage = false;  // 【新增】标记是否收到首条消息

        // 【新增】从 ref 获取初始超时时间，默认 30 秒
        const INITIAL_TIMEOUT = initialTimeoutRef.current || 30000;
        const NORMAL_TIMEOUT = 30000;
        const HEARTBEAT_CHECK_INTERVAL = 5000;

        heartbeatCheckerRef.current = setInterval(() => {
            const elapsed = Date.now() - lastMessageTime;

            // 【修改】根据是否收到首条消息决定超时阈值
            const timeoutThreshold = hasReceivedFirstMessage ? NORMAL_TIMEOUT : INITIAL_TIMEOUT;

            if (elapsed > timeoutThreshold) {
                const timeoutType = hasReceivedFirstMessage ? '正常执行超时' : '首次连接超时';
                console.error(`SSE ${timeoutType} (${elapsed}ms > ${timeoutThreshold}ms)`);
                handleTaskCompletion('failed', { error: "连接超时，后端可能已停止" });

                // 强制更新步骤状态为失败
                setSteps(prev => prev.map(s =>
                    (s.status === 'running' || s.status === 'pending')
                        ? { ...s, status: 'failed', message: '连接超时' }
                        : s
                ));

                // 清理资源
                cleanupSSE();
            }
        }, HEARTBEAT_CHECK_INTERVAL);

        // [Fix] Listen for explicit system_error events from backend
        eventSource.addEventListener('system_error', (event: MessageEvent) => {
            console.error("SSE System Error:", event.data);
            handleTaskCompletion('failed', { error: event.data || "生成出错" });
            // Force update steps to failed
            setSteps(prev => prev.map(s =>
                (s.status === 'running' || s.status === 'pending')
                    ? { ...s, status: 'failed', message: '任务中断' }
                    : s
            ));
        });

        eventSource.addEventListener('progress', (event: MessageEvent) => {
            lastMessageTime = Date.now(); // 【新增】重置心跳时间戳
            hasReceivedFirstMessage = true;  // 【新增】标记已收到首条消息

            // 【新增】收到首条消息后重置超时时间（清除初始超时设置）
            if (initialTimeoutRef.current) {
                initialTimeoutRef.current = null;
            }

            try {
                const data = JSON.parse(event.data);

                // 更新步骤状态
                if (data.steps) {
                    updateSteps(data.steps);
                }

                // [修复] 检查任务是否结束，支持三种状态
                if (data.status === 'completed') {
                    console.log("任务成功完成:", id);
                    handleTaskCompletion('completed', data);
                } else if (data.status === 'stopped') {
                    // [新增] 处理提前终止状态
                    console.log("任务提前终止:", id);
                    handleTaskCompletion('stopped', data);
                    // 更新步骤状态为 stopped
                    setSteps(prev => prev.map(s =>
                        (s.status === 'running' || s.status === 'pending')
                            ? { ...s, status: 'completed', message: '已停止' }
                            : s
                    ));
                } else if (data.status === 'failed') {
                    console.log("任务执行失败:", id);
                    handleTaskCompletion('failed', data);
                    // 强制更新步骤状态为 failed
                    setSteps(prev => prev.map(s =>
                        (s.status === 'running' || s.status === 'pending')
                            ? { ...s, status: 'failed', message: '任务失败' }
                            : s
                    ));
                }
            } catch (e) {
                console.error("Error parsing SSE data", e);
            }
        });

        eventSource.onerror = (err) => {
            console.error("SSE Error:", err);
            // [修复] 连接错误作为失败处理
            handleTaskCompletion('failed', { error: "连接中断，任务可能已停止" });

            // Force update steps to failed
            setSteps(prev => prev.map(s =>
                (s.status === 'running' || s.status === 'pending')
                    ? { ...s, status: 'failed', message: '连接中断' }
                    : s
            ));
        };
    };

    const updateSteps = (backendSteps: any[]) => {
        setSteps(prevSteps => {
            // 如果 prevSteps 为空（例如刚刷新页面），则直接映射 backendSteps
            // 但我们需要保持 label 信息，所以这里假设 backendSteps 包含了必要信息，或者我们需要从常量中恢复
            // 简化起见，我们假设 ManualReportPage 会初始化 steps，或者我们在这里做合并

            // 如果是全新的 steps (例如从 localStorage 恢复后第一次收到数据)
            if (prevSteps.length === 0) {
                // 这里可能丢失 label，但在 ManualReportPage 中渲染时通常会结合静态配置
                return backendSteps.map((s: any) => ({
                    name: s.name,
                    label: WORKFLOW_STEP_LABELS[s.name] || s.name, // Use shared label or fallback to name
                    status: s.status,
                    progress: s.progress?.current ? Math.round((s.progress.current / s.progress.total) * 100) : 0,
                    current: s.progress?.current,
                    total: s.progress?.total,
                    message: s.progress?.message,
                    duration_ms: s.duration_ms
                }));
            }

            const newSteps = [...prevSteps];
            backendSteps.forEach((bStep: any) => {
                const index = newSteps.findIndex(s => s.name === bStep.name);
                if (index !== -1) {
                    const currentStep = { ...newSteps[index] };
                    currentStep.status = bStep.status;
                    currentStep.duration_ms = bStep.duration_ms;

                    if (bStep.progress) {
                        const { current, total, message } = bStep.progress;
                        if (total > 0) currentStep.progress = Math.round((current / total) * 100);
                        currentStep.current = current;
                        currentStep.total = total;
                        if (message) currentStep.message = message;
                    } else if (bStep.status === 'completed') {
                        currentStep.progress = 100;
                        currentStep.message = "完成";
                    } else if (bStep.status === 'running') {
                        if (!currentStep.message) currentStep.message = "正在执行...";
                    }
                    newSteps[index] = currentStep;
                }
            });
            return newSteps;
        });
    };

    /**
     * 处理任务完成的统一函数
     * 
     * 功能：根据不同的执行状态（completed/stopped/failed）显示不同的UI反馈
     * 
     * @param status - 执行状态（completed=成功完成，stopped=提前终止，failed=执行失败）
     * @param data - 执行数据，包含 metadata、error 等信息
     */
    const handleTaskCompletion = useCallback((status: string, data: any) => {
        // 防止重复完成
        if (completedRef.current) {
            console.log("[WARN] 任务已完成，忽略重复调用");
            return;
        }
        completedRef.current = true;

        console.log("处理任务完成:", { status, data });

        // 清理 SSE 连接
        cleanupSSE();

        // 更新状态
        setIsGenerating(false);

        // 清理 localStorage
        localStorage.removeItem('current_manual_execution_id');

        // 根据状态决定行为
        let toastMessage = "";
        let toastType: "success" | "error" | "warning" = "success";
        let shouldNavigate = false;

        if (status === 'completed') {
            // 成功完成
            toastMessage = "报告生成成功！";
            toastType = "success";
            shouldNavigate = true;
        } else if (status === 'stopped') {
            // 提前终止（如无结果）
            // 从 metadata 中读取详细消息
            let metadata: any = {};
            try {
                metadata = typeof data.metadata === 'string'
                    ? JSON.parse(data.metadata)
                    : data.metadata || {};
            } catch (e) {
                console.error("解析 metadata 失败:", e);
            }

            const stopMessage = metadata.stop_message ||
                "未找到符合您查询条件的论文，请尝试调整关键词或放宽筛选条件。";
            toastMessage = stopMessage;
            toastType = "warning";
            shouldNavigate = false; // 留在当前页
        } else if (status === 'failed') {
            // 真正失败
            const errorMessage = data.error || "任务执行失败";
            toastMessage = errorMessage;
            toastType = "error";
            shouldNavigate = false; // 留在当前页
        }

        // 显示通知
        showToast(toastMessage, toastType);

        // 如果需要跳转到报告列表
        if (shouldNavigate) {
            // 只有成功时才 invalidate queries
            queryClient.invalidateQueries({ queryKey: ['reports'] });
            // 同时刷新用户画像，以更新额度显示
            queryClient.invalidateQueries({ queryKey: ['userProfile'] });

            if (navigationRef.current) {
                setTimeout(() => {
                    navigationRef.current?.('reports');
                }, 1000);
            }
        }

        // 重置状态
        setTimeout(() => {
            setExecutionId(null);
            setSteps([]);
            completedRef.current = false; // 重置以便下次任务
        }, shouldNavigate ? 1500 : 2000); // 不跳转时稍微延迟重置
    }, [queryClient, showToast]);

    /**
     * 开始一个新任务
     * 
     * @param executionId - 任务执行 ID
     * @param initialSteps - 初始步骤列表
     */
    const startTask = (executionId: string, initialSteps: StepProgress[]) => {
        console.log("Starting task:", executionId);
        setExecutionId(executionId);
        setSteps(initialSteps);
        setIsGenerating(true);
        localStorage.setItem('current_manual_execution_id', executionId);
    };

    /**
     * 停止当前任务
     */
    const stopTask = useCallback(() => {
        console.log("Stopping task");
        setIsGenerating(false);
        setExecutionId(null);
        setSteps([]);
        localStorage.removeItem('current_manual_execution_id');
        cleanupSSE();
    }, []);

    const registerNavigation = useCallback((fn: (view: string, data?: any) => void) => {
        navigationRef.current = fn;
    }, []);

    // [New] Restore state from Server or LocalStorage
    useEffect(() => {
        const restoreState = async () => {
            try {
                // 1. 先检查服务器是否有活跃执行
                const result = await WorkflowAPI.getActiveExecution();

                if (result.active && result.execution_id && result.steps) {
                    console.log("发现活跃任务，开始验证:", result.execution_id);

                    // 2. 【新增】验证任务是否真的在运行
                    try {
                        const verification = await WorkflowAPI.verifyExecution(result.execution_id, { timeout: 3000 });

                        if (verification.active) {
                            // 3. 验证通过，恢复任务
                            console.log("任务验证通过，恢复状态:", verification.message);

                            const mappedSteps = result.steps.map((s: any) => ({
                                name: s.name,
                                label: WORKFLOW_STEP_LABELS[s.name] || s.name,
                                status: s.status,
                                progress: s.progress?.current ? Math.round((s.progress.current / s.progress.total) * 100) : 0,
                                current: s.progress?.current,
                                total: s.progress?.total,
                                message: s.progress?.message,
                                duration_ms: s.duration_ms
                            }));

                            // 【修改】恢复任务时标记使用短超时
                            setExecutionId(result.execution_id);
                            setSteps(mappedSteps);
                            setIsGenerating(true);
                            localStorage.setItem('current_manual_execution_id', result.execution_id);
                            // 设置初始超时为 5 秒
                            initialTimeoutRef.current = 5000;
                            return;
                        } else {
                            // 4. 验证失败，清理状态
                            console.warn(`任务验证失败: ${verification.reason} - ${verification.message}`);
                            localStorage.removeItem('current_manual_execution_id');

                            // 【可选】显示 Toast 提示
                            showToast(`检测到异常任务，已自动清理（${verification.message}）`, 'error');

                            // 确保状态清理
                            if (isGenerating) {
                                setIsGenerating(false);
                                setExecutionId(null);
                                setSteps([]);
                            }
                            return;
                        }
                    } catch (verifyError: any) {
                        // 5. 验证接口失败（后端可能崩溃）
                        console.error("验证接口失败:", verifyError);
                        localStorage.removeItem('current_manual_execution_id');

                        showToast('无法连接到后端，任务状态已清理', 'error');

                        if (isGenerating) {
                            setIsGenerating(false);
                            setExecutionId(null);
                            setSteps([]);
                        }
                        return;
                    }
                } else {
                    // 6. 服务器说没有活跃执行，清除本地状态
                    console.log("服务器无活跃任务，清理本地状态");
                    localStorage.removeItem('current_manual_execution_id');

                    if (isGenerating) {
                        setIsGenerating(false);
                        setExecutionId(null);
                        setSteps([]);
                    }
                    return;
                }
            } catch (err: any) {
                console.error("恢复状态失败", err);

                // 任何错误都清理状态，不 fallback
                localStorage.removeItem('current_manual_execution_id');

                if (err?.status === 401 || err?.status === 403) {
                    // 401/403 不显示错误提示
                    console.log("Unauthorized/Forbidden. Clearing localStorage.");
                    return;
                }

                // 其他错误显示提示
                showToast('无法连接到后端', 'error');
                return;
            }
        };

        restoreState();
    }, []); // ✅ 只在组件挂载时执行一次，避免无限循环

    return (
        <TaskContext.Provider value={{
            isGenerating,
            executionId,
            steps,
            startTask,
            stopTask,
            registerNavigation
        }}>
            {children}
        </TaskContext.Provider>
    );
};

export const useTaskContext = () => {
    const context = useContext(TaskContext);
    if (!context) {
        throw new Error('useTaskContext must be used within a TaskProvider');
    }
    return context;
};
