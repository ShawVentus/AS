import React, { useState } from 'react';
import { WorkflowAPI } from '../../services/api';
import { useWorkflowProgress } from '../../hooks/useWorkflowProgress';
import { WorkflowProgress } from '../../components/features/workflow/WorkflowProgress';

export const WorkflowPage: React.FC = () => {
    const [executionId, setExecutionId] = useState<string>('');
    const [resumeId, setResumeId] = useState<string>('');
    const { progress, isConnected, error, startMonitoring } = useWorkflowProgress();
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    const handleTriggerDaily = async () => {
        setLoading(true);
        setMessage(null);
        try {
            // 触发工作流
            // 注意：后端目前是异步触发，返回 message，但不一定返回 execution_id (取决于实现)
            // 如果后端修改为返回 execution_id 更好。
            // 假设后端 trigger-daily 返回 { message: "...", execution_id: "..." } (需要修改后端)
            // 或者我们先触发，然后通过 SSE 监听最新的？或者手动输入 ID？
            // 暂时假设用户需要手动输入 ID 或者我们在控制台看日志...
            // 为了演示，我们修改后端让 trigger-daily 返回 execution_id，或者我们先只显示触发成功。

            const res = await WorkflowAPI.triggerDaily();
            setMessage(`工作流已触发: ${res.message}`);

            if (res.execution_id) {
                setExecutionId(res.execution_id);
                startMonitoring(res.execution_id);
            }
        } catch (err: any) {
            setMessage(`触发失败: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleResume = async () => {
        if (!resumeId) return;
        setLoading(true);
        try {
            const res = await WorkflowAPI.resumeWorkflow(resumeId);
            setMessage(res.message);
            // 开始监听
            startMonitoring(resumeId);
            setExecutionId(resumeId);
        } catch (err: any) {
            setMessage(`恢复失败: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleMonitor = () => {
        if (executionId) {
            startMonitoring(executionId);
        }
    };

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-2xl font-bold mb-6">工作流管理控制台</h1>

            <div className="bg-white shadow rounded-lg p-6 mb-8">
                <h2 className="text-lg font-semibold mb-4">操作</h2>

                <div className="flex flex-col space-y-4 md:flex-row md:space-y-0 md:space-x-4">
                    {/* 触发每日工作流 */}
                    <div className="p-4 border rounded bg-gray-50 flex-1">
                        <h3 className="font-medium mb-2">每日更新</h3>
                        <button
                            onClick={handleTriggerDaily}
                            disabled={loading}
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                            {loading ? '处理中...' : '🚀 立即触发每日更新'}
                        </button>
                    </div>

                    {/* 恢复工作流 */}
                    <div className="p-4 border rounded bg-gray-50 flex-1">
                        <h3 className="font-medium mb-2">断点恢复</h3>
                        <div className="flex space-x-2">
                            <input
                                type="text"
                                placeholder="Execution ID"
                                value={resumeId}
                                onChange={(e) => setResumeId(e.target.value)}
                                className="border rounded px-3 py-2 flex-1"
                            />
                            <button
                                onClick={handleResume}
                                disabled={loading || !resumeId}
                                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                            >
                                恢复
                            </button>
                        </div>
                    </div>

                    {/* 监控特定 ID */}
                    <div className="p-4 border rounded bg-gray-50 flex-1">
                        <h3 className="font-medium mb-2">监控进度</h3>
                        <div className="flex space-x-2">
                            <input
                                type="text"
                                placeholder="Execution ID"
                                value={executionId}
                                onChange={(e) => setExecutionId(e.target.value)}
                                className="border rounded px-3 py-2 flex-1"
                            />
                            <button
                                onClick={handleMonitor}
                                disabled={!executionId}
                                className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
                            >
                                监控
                            </button>
                        </div>
                    </div>
                </div>

                {message && (
                    <div className="mt-4 p-3 bg-blue-50 text-blue-700 rounded">
                        {message}
                    </div>
                )}
            </div>

            {/* 实时进度 */}
            <WorkflowProgress progress={progress} isConnected={isConnected} error={error} />
        </div>
    );
};
