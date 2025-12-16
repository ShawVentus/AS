export interface StepProgress {
    name: string;
    label: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    current?: number;
    total?: number;
    message?: string;
    duration_ms?: number;
}
