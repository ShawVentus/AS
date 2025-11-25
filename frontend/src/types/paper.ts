export interface PaperDetails {
    /** 研究动机 */
    motivation: string;
    /** 研究方法 */
    method: string;
    /** 实验结果 */
    result: string;
    /** 结论 */
    conclusion: string;
    /** 摘要 (已移至外层，此处保留兼容或移除) -> 移除 */
    // abstract: string; 
}

export interface PaperLinks {
    /** PDF链接 */
    pdf: string;
    /** Arxiv链接 */
    arxiv: string;
    /** HTML页面链接 */
    html: string;
}

export interface UserPaperState {
    paper_id: string;
    user_id: string;
    /** 相关度评分 (0-1) */
    relevance_score: number;
    /** 推荐理由 */
    why_this_paper?: string;
    /** LLM 建议是否接受 */
    accepted: boolean;
    /** 用户是否接受 (加入报告) */
    user_accepted: boolean;
    /** 用户是否喜欢 */
    user_liked?: boolean | null;
    /** 用户反馈 */
    user_feedback?: string;
}

export interface PaperMetadata {
    /** 论文ID */
    id: string;
    /** 标题 */
    title: string;
    /** 作者列表 */
    authors: string[];
    /** 发布日期 */
    published_date: string;
    /** 分类 (如 cs.LG) */
    category: string[]; // Backend returns list
    /** 摘要 */
    abstract: string;
    /** 备注 */
    comment?: string;
    /** 一句话总结 */
    tldr?: string;
    /** 阅读建议 (如: 精读, 略读) */
    suggestion?: string;
    /** 标签列表 (通用) */
    tags: string[];
    /** 详细信息 */
    details?: PaperDetails;
    /** 相关链接 */
    links: PaperLinks;
    /** 引用数 */
    citationCount: number;
    /** 年份 */
    year?: number;
}

export interface PersonalizedPaper extends PaperMetadata {
    /** 用户个性化状态 */
    user_state?: UserPaperState;
}

// Alias for backward compatibility during refactor, or use PersonalizedPaper directly
export type Paper = PersonalizedPaper;

export interface PaperAnalysis {
    /** 分析摘要 */
    summary: string;
    /** 核心要点 */
    key_points: PaperDetails;
    /** 推荐理由 */
    recommendation_reason: string;
    /** 评分 */
    score: number;
    /** 是否接受 */
    accepted: boolean;
}
