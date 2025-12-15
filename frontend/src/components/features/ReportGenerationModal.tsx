import React, { useEffect, useState, useRef } from 'react';
import { WorkflowAPI } from '../../services/api';
import { X, CheckCircle, Circle, Loader2, AlertCircle, Clock, ChevronRight } from 'lucide-react';

interface ReportGenerationModalProps {
    isOpen: boolean;
    onClose: () => void;
    userId: string;
    onComplete?: () => void;
}

interface StepProgress {
    name: string;
    label: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number; // 0-100
    message?: string;
    duration_ms?: number;
}

const STEPS: { name: string; label: string }[] = [
    { name: 'run_crawler', label: '爬取新论文' },
    { name: 'fetch_details', label: '获取详情' },
    { name: 'analyze_public_papers', label: '公共分析' },
    { name: 'archive_daily_papers', label: '归档论文' },
    { name: 'personalized_filter', label: '个性化筛选' },
    { name: 'generate_report', label: '生成报告' }
];

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
                <div ref={scrollRef} className="p-6 overflow-y-auto flex-1 scroll-smooth">
                    <div className="space-y-0">
                        {steps.map((step, index) => {
                            const isLast = index === steps.length - 1;
                            const isActive = step.status === 'running';
                            const isCompletedStep = step.status === 'completed';
                            const isFailed = step.status === 'failed';
                            const isPending = step.status === 'pending';

                            return (
                                <div key={step.name} className="relative flex gap-4">
                                    {/* Left Timeline Line */}
                                    {!isLast && (
                                        <div
                                            className={`absolute left-[15px] top-[30px] bottom-[-20px] w-[2px] 
                                            ${isCompletedStep ? 'bg-green-200 dark:bg-green-900/50' : 'bg-gray-100 dark:bg-gray-800'}`}
                                        />
                                    )}

                                    {/* Icon Indicator */}
                                    <div className={`relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300
                                        ${isCompletedStep ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' :
                                            isActive ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 ring-4 ring-blue-50 dark:ring-blue-900/20' :
                                                isFailed ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                                                    'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'
                                        }`}
                                    >
                                        {isCompletedStep ? (
                                            <CheckCircle size={18} />
                                        ) : isActive ? (
                                            <div className="w-3 h-3 bg-blue-600 rounded-full animate-ping" />
                                        ) : isFailed ? (
                                            <AlertCircle size={18} />
                                        ) : (
                                            <Circle size={18} />
                                        )}
                                    </div>

                                    {/* Content */}
                                    <div className={`flex-1 pb-8 ${isPending ? 'opacity-50' : 'opacity-100'} transition-opacity duration-300`}>
                                        <div className="flex justify-between items-start">
                                            <h3 className={`font-medium text-base ${isActive ? 'text-blue-600 dark:text-blue-400' :
                                                isCompletedStep ? 'text-gray-900 dark:text-gray-100' :
                                                    'text-gray-500 dark:text-gray-500'
                                                }`}>
                                                {step.label}
                                            </h3>
                                            {step.duration_ms && (
                                                <span className="text-xs text-gray-400 flex items-center gap-1 bg-gray-50 dark:bg-gray-800/50 px-2 py-0.5 rounded-full">
                                                    <Clock size={10} />
                                                    {(step.duration_ms / 1000).toFixed(1)}s
                                                </span>
                                            )}
                                        </div>

                                        {/* Dynamic Message */}
                                        {(isActive || step.message) && (
                                            <div className={`mt-2 text-sm flex items-center gap-2 
                                                ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'}`}
                                            >
                                                {isActive && <Loader2 size={12} className="animate-spin" />}
                                                <span>{step.message || (isActive ? "正在处理..." : "")}</span>
                                            </div>
                                        )}

                                        {/* Progress Bar (Only for running step) */}
                                        {isActive && step.progress > 0 && (
                                            <div className="mt-3 h-1.5 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-blue-500 rounded-full transition-all duration-300 ease-out"
                                                    style={{ width: `${step.progress}%` }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

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
