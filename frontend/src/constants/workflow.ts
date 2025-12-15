
export const WORKFLOW_STEPS = [
    { name: 'run_crawler', label: '爬取新论文' },
    { name: 'fetch_details', label: '获取详情' },
    { name: 'analyze_public_papers', label: '公共分析' },
    { name: 'archive_daily_papers', label: '归档论文' },
    { name: 'personalized_filter', label: '个性化筛选' },
    { name: 'generate_report', label: '生成报告' }
] as const;

export const WORKFLOW_STEP_LABELS: Record<string, string> = WORKFLOW_STEPS.reduce((acc, step) => {
    acc[step.name] = step.label;
    return acc;
}, {} as Record<string, string>);
