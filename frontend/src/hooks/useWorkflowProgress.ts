import { useState, useEffect, useCallback } from 'react';

// 定义进度数据类型
export interface WorkflowStep {
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
    duration_ms: number;
    cost: number;
}

export interface WorkflowProgress {
    execution_id: string;
    status: string;
    current_step: string;
    total_steps: number;
    completed_steps: number;
    total_cost: number;
    steps: WorkflowStep[];
}

export const useWorkflowProgress = () => {
    const [progress, setProgress] = useState<WorkflowProgress | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const startMonitoring = useCallback((executionId: string) => {
        // 关闭旧连接
        setProgress(null);
        setError(null);

        const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const url = `${backendUrl}/api/v1/workflow/progress-stream/${executionId}`;

        console.log(`Connecting to SSE: ${url}`);
        const eventSource = new EventSource(url);

        eventSource.onopen = () => {
            console.log('SSE Connected');
            setIsConnected(true);
        };

        eventSource.onmessage = (event) => {
            try {
                // SSE 格式: data: {...}
                // 但 EventSource 会自动解析 data 部分
                const data = JSON.parse(event.data);
                setProgress(data);

                if (data.status === 'completed' || data.status === 'failed') {
                    eventSource.close();
                    setIsConnected(false);
                }
            } catch (err) {
                console.error('Error parsing SSE data:', err);
            }
        };

        eventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            setError('Connection lost');
            eventSource.close();
            setIsConnected(false);
        };

        // 监听自定义事件 'progress' (如果后端发送 event: progress)
        eventSource.addEventListener('progress', (event: MessageEvent) => {
            try {
                const data = JSON.parse(event.data);
                setProgress(data);
                if (data.status === 'completed' || data.status === 'failed') {
                    eventSource.close();
                    setIsConnected(false);
                }
            } catch (err) {
                console.error('Error parsing progress event:', err);
            }
        });

        eventSource.addEventListener('error', (event: MessageEvent) => {
            // 后端发送 event: error
            console.error('SSE Server Error:', event.data);
            setError(event.data);
            eventSource.close();
            setIsConnected(false);
        });

        return () => {
            eventSource.close();
            setIsConnected(false);
        };
    }, []);

    return { progress, isConnected, error, startMonitoring };
};
