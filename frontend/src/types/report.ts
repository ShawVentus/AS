export interface ReportContent {
    /** 段落文本 */
    text: string;
    /** 引用论文ID列表 */
    refIds: string[];
}

export interface Report {
    /** 报告ID */
    id: string;
    /** 标题 */
    title: string;
    /** 日期 */
    date: string;
    /** 摘要 */
    summary: string;
    /** 内容段落列表 */
    content: ReportContent[];
}
