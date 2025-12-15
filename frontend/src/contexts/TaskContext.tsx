import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from './ToastContext';
import { WORKFLOW_STEP_LABELS } from '../constants/workflow';

export interface StepProgress {
    name: string;
    label: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    message?: string;
    duration_ms?: number;
}

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
    const { showToast } = useToast();
    const queryClient = useQueryClient();

    // 从 localStorage 恢复状态
    useEffect(() => {
        const storedId = localStorage.getItem('current_manual_execution_id');
        if (storedId) {
            console.log("Restoring task from localStorage:", storedId);
            setExecutionId(storedId);
            setIsGenerating(true);
            // 恢复时，steps 可能为空，需要通过 SSE 或 API 获取最新状态
            // 这里我们依赖 SSE 连接后收到的第一条消息来更新 steps
        }
    }, []);

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
    };

    const connectToSSE = (id: string) => {
        if (eventSourceRef.current?.url.includes(id)) return; // 避免重复连接

        console.log("Connecting to SSE for execution:", id);
        const url = `${import.meta.env.VITE_API_BASE_URL || '/api'}/workflow/progress-stream/${id}`;
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        eventSource.addEventListener('progress', (event: MessageEvent) => {
            try {
                const data = JSON.parse(event.data);

                // 更新步骤状态
                if (data.steps) {
                    updateSteps(data.steps);
                }

                // 检查任务是否结束
                if (data.status === 'completed') {
                    console.log("Task completed:", id);
                    completeTask(true);
                } else if (data.status === 'failed') {
                    console.log("Task failed:", id);
                    completeTask(false, data.error);
                }
            } catch (e) {
                console.error("Error parsing SSE data", e);
            }
        });

        eventSource.onerror = (err) => {
            console.error("SSE Error:", err);
            // 连接错误通常意味着连接中断，EventSource 会自动重连
            // 但如果是 404 或其他致命错误，可能需要手动处理
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

    const completeTask = (success: boolean, error?: string) => {
        setIsGenerating(false);
        setExecutionId(null);
        localStorage.removeItem('current_manual_execution_id');
        cleanupSSE();

        if (success) {
            // Invalidate queries to ensure fresh data
            queryClient.invalidateQueries({ queryKey: ['reports'] });
            queryClient.invalidateQueries({ queryKey: ['userProfile'] }); // Update photons

            showToast("今日研报生成完成！", 'success', {
                duration: 5000,
                action: {
                    label: "立即查看",
                    onClick: () => {
                        if (navigationRef.current) {
                            navigationRef.current('reports', { selectLatest: true });
                        } else {
                            window.location.reload();
                        }
                    }
                }
            });
        } else {
            showToast(`生成失败: ${error || '未知错误'}`, 'error');
        }
    };

    const startTask = useCallback((id: string, initialSteps: StepProgress[]) => {
        setExecutionId(id);
        setSteps(initialSteps);
        setIsGenerating(true);
        localStorage.setItem('current_manual_execution_id', id);
    }, []);

    const stopTask = useCallback(() => {
        setIsGenerating(false);
        setExecutionId(null);
        setSteps([]);
        localStorage.removeItem('current_manual_execution_id');
        cleanupSSE();
    }, []);

    const registerNavigation = useCallback((fn: (view: string, data?: any) => void) => {
        navigationRef.current = fn;
    }, []);

    return (
        <TaskContext.Provider value={{ isGenerating, executionId, steps, startTask, stopTask, registerNavigation }}>
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
