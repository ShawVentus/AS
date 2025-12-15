import React, { useEffect, useState, useRef } from 'react';
import { WorkflowAPI } from '../../services/api';
import { X, CheckCircle, Loader2, AlertCircle, ChevronRight } from 'lucide-react';
import { WorkflowProgress } from './workflow/WorkflowProgress';
import type { StepProgress } from '../../contexts/TaskContext';

interface ReportGenerationModalProps {
    isOpen: boolean;
    onClose: () => void;
    userId: string;
    onComplete?: () => void;
}



import { WORKFLOW_STEPS } from '../../constants/workflow';

const STEPS = WORKFLOW_STEPS;

export const ReportGenerationModal: React.FC<ReportGenerationModalProps> = ({ isOpen, onClose, userId, onComplete }) => {
    const [steps, setSteps] = useState<StepProgress[]>(
        STEPS.map(s => ({ ...s, status: 'pending', progress: 0 }))
    );
    const [error, setError] = useState<string | null>(null);
    const [isCompleted, setIsCompleted] = useState(false);
    const eventSourceRef = useRef<EventSource | null>(null);
    const hasTriggeredRef = useRef(false);
    const scrollRef = useRef<HTMLDivElement>(null);

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
            cleanupSSE();
        };
    }, [isOpen]);

    const cleanupSSE = () => {
        if (eventSourceRef.current) {
            console.log("Closing SSE connection...");
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    };

    const startGeneration = async () => {
        hasTriggeredRef.current = true;
        setError(null);
        setIsCompleted(false);
        setSteps(STEPS.map(s => ({ ...s, status: 'pending', progress: 0 })));

        try {
            const { execution_id } = await WorkflowAPI.triggerDaily(userId);

            if (execution_id) {
                connectToSSE(execution_id);
            } else {
                setError("无法获取执行 ID");
            }
        } catch (err: any) {
            setError(err.message || "启动失败");
        }
    };

    const connectToSSE = (executionId: string) => {
        // Close existing connection if any
        cleanupSSE();

        const url = `${import.meta.env.VITE_API_BASE_URL || '/api'}/workflow/progress-stream/${executionId}`;
        console.log(`Connecting to SSE: ${url}`);

        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        // [Fix] Listen for named 'progress' event
        eventSource.addEventListener('progress', (event: MessageEvent) => {
            try {
                const data = JSON.parse(event.data);
                // console.log("SSE Data:", data);

                if (data.steps) {
                    updateSteps(data.steps);
                }

                if (data.status === 'completed') {
                    setIsCompleted(true);
                    cleanupSSE(); // Stop reconnection loop
                    if (onComplete) onComplete();
                    return;
                }
            } catch (e) {
                console.error("Error parsing SSE data", e);
            }
        });

        eventSource.onerror = (err) => {
            console.error("SSE Error", err);
            // If the connection was closed intentionally, don't treat as error
            if (eventSource.readyState === EventSource.CLOSED) {
                return;
            }
            // Optional: cleanup on error to prevent infinite loops if backend is down
            // cleanupSSE(); 
        };
    };

    const updateSteps = (backendSteps: any[]) => {
        setSteps(prevSteps => {
            const newSteps = [...prevSteps];

            backendSteps.forEach((bStep: any) => {
                const index = newSteps.findIndex(s => s.name === bStep.name);
                if (index !== -1) {
                    const currentStep = { ...newSteps[index] };

                    // Update status
                    currentStep.status = bStep.status;
                    currentStep.duration_ms = bStep.duration_ms;

                    // Update progress
                    if (bStep.progress) {
                        const { current, total, message } = bStep.progress;
                        if (total > 0) {
                            currentStep.progress = Math.round((current / total) * 100);
                        }
                        if (message) {
                            currentStep.message = message;
                        }
                    } else if (bStep.status === 'completed') {
                        currentStep.progress = 100;
                        currentStep.message = "完成";
                    } else if (bStep.status === 'running') {
                        // Default message for running state if none provided
                        if (!currentStep.message) currentStep.message = "正在执行...";
                    }

                    newSteps[index] = currentStep;
                }
            });

            return newSteps;
        });
    };

    const handleClose = () => {
        cleanupSSE();
        hasTriggeredRef.current = false;
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm transition-all duration-300">
            <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in duration-300 border border-gray-100 dark:border-gray-800">

                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-white/50 dark:bg-gray-900/50 backdrop-blur-md sticky top-0 z-10">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                            {isCompleted ? (
                                <>
                                    <CheckCircle className="text-green-500 w-6 h-6" />
                                    <span>生成完成</span>
                                </>
                            ) : (
                                <>
                                    <Loader2 className="animate-spin text-blue-600 w-6 h-6" />
                                    <span>正在生成报告...</span>
                                </>
                            )}
                        </h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {isCompleted ? "您的日报已发送至邮箱" : "请稍候，正在处理您的订阅内容"}
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
