import React from 'react';
import { WorkflowProgress as WorkflowProgressType } from '../../hooks/useWorkflowProgress';

interface Props {
    progress: WorkflowProgressType | null;
    isConnected: boolean;
    error: string | null;
}

export const WorkflowProgress: React.FC<Props> = ({ progress, isConnected, error }) => {
    if (error) {
        return <div className="text-red-500 p-4 bg-red-50 rounded">Error: {error}</div>;
    }

    if (!progress && !isConnected) {
        return null;
    }

    if (!progress && isConnected) {
        return <div className="text-gray-500 p-4">Connecting to workflow stream...</div>;
    }

    if (!progress) return null;

    const percent = Math.round((progress.completed_steps / progress.total_steps) * 100);

    return (
        <div className="bg-white shadow rounded-lg p-6 max-w-2xl mx-auto mt-4">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800">工作流进度</h2>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${progress.status === 'running' ? 'bg-blue-100 text-blue-800' :
                        progress.status === 'completed' ? 'bg-green-100 text-green-800' :
                            progress.status === 'failed' ? 'bg-red-100 text-red-800' :
                                'bg-gray-100 text-gray-800'
                    }`}>
                    {progress.status.toUpperCase()}
                </span>
            </div>

            {/* 进度条 */}
            <div className="w-full bg-gray-200 rounded-full h-4 mb-6">
                <div
                    className={`h-4 rounded-full transition-all duration-500 ${progress.status === 'failed' ? 'bg-red-500' : 'bg-blue-600'
                        }`}
                    style={{ width: `${percent}%` }}
                ></div>
            </div>

            <div className="flex justify-between text-sm text-gray-600 mb-6">
                <span>步骤: {progress.completed_steps} / {progress.total_steps}</span>
                <span>总成本: ${progress.total_cost?.toFixed(6) || '0.000000'}</span>
            </div>

            {/* 步骤列表 */}
            <div className="space-y-3">
                {progress.steps.map((step, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded border border-gray-100">
                        <div className="flex items-center space-x-3">
                            <div className={`w-2 h-2 rounded-full ${step.status === 'completed' ? 'bg-green-500' :
                                    step.status === 'running' ? 'bg-blue-500 animate-pulse' :
                                        step.status === 'failed' ? 'bg-red-500' :
                                            'bg-gray-300'
                                }`}></div>
                            <span className="font-medium text-gray-700">{step.name}</span>
                        </div>
                        <div className="flex items-center space-x-4 text-sm">
                            {step.duration_ms > 0 && (
                                <span className="text-gray-500">{(step.duration_ms / 1000).toFixed(1)}s</span>
                            )}
                            {step.cost > 0 && (
                                <span className="text-gray-500">${step.cost.toFixed(6)}</span>
                            )}
                            <span className={`text-xs px-2 py-0.5 rounded ${step.status === 'completed' ? 'bg-green-100 text-green-700' :
                                    step.status === 'running' ? 'bg-blue-100 text-blue-700' :
                                        step.status === 'failed' ? 'bg-red-100 text-red-700' :
                                            'bg-gray-200 text-gray-600'
                                }`}>
                                {step.status}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
