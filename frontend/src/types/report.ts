export interface Report {
    /** 报告ID */
    id: string;
    /** 标题 */
    title: string;
    /** 日期 */
    date: string;
    /** 创建时间 (ISO 8601) */
    createdAt?: string;
    created_at?: string;
    /** 摘要 */
    summary: string;
    /** 内容 (Markdown 格式) */
    content: string;
    /** 引用的论文 ID 列表 */
    refPapers: string[];
}
