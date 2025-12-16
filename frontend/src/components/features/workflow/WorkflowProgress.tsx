import React, { useEffect, useRef } from 'react';
import { CheckCircle, Circle, Loader2, AlertCircle } from 'lucide-react';
import type { StepProgress } from '../../../types/workflow';

interface WorkflowProgressProps {
    steps: StepProgress[]; // 步骤列表
}

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({ steps }) => {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when steps update
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [steps]);

    return (
        <div ref={scrollRef} className="p-6 overflow-y-auto flex-1 scroll-smooth h-full">
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
                                    className={`absolute left-[23px] top-[30px] bottom-[-20px] w-[2px] 
                                    ${isCompletedStep ? 'bg-green-200 dark:bg-green-900/50' : 'bg-gray-100 dark:bg-gray-800'}`}
                                />
                            )}

                            {/* Icon Indicator */}
                            <div className={`relative z-10 flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300
                                ${isCompletedStep ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' :
                                    isActive ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 ring-4 ring-blue-50 dark:ring-blue-900/20' :
                                        isFailed ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                                            'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'
                                }`}
                            >
                                {isCompletedStep ? (
                                    <CheckCircle size={24} />
                                ) : isActive ? (
                                    <div className="w-5 h-5 bg-blue-600 rounded-full animate-ping" />
                                ) : isFailed ? (
                                    <AlertCircle size={24} />
                                ) : (
                                    <Circle size={24} />
                                )}
                            </div>

                            {/* Content */}
                            <div className={`flex-1 pb-8 ${isPending ? 'opacity-50' : 'opacity-100'} transition-opacity duration-300`}>
                                <div className="flex justify-between items-start">
                                    <h3 className={`font-medium text-xl ${isActive ? 'text-blue-600 dark:text-blue-400' :
                                        isCompletedStep ? 'text-gray-900 dark:text-gray-100' :
                                            'text-gray-500 dark:text-gray-500'
                                        }`}>
                                        {step.label}
                                    </h3>
                                </div>

                                {/* Dynamic Message */}
                                {(isActive || step.message) && (
                                    <div className={`mt-2 text-lg flex items-center gap-2 
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
    );
};
