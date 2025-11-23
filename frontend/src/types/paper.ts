export interface PaperDetails {
    /** 研究动机 */
    motivation: string;
    /** 研究方法 */
    method: string;
    /** 实验结果 */
    result: string;
    /** 结论 */
    conclusion: string;
    /** 摘要 */
    abstract: string;
    /** 一句话总结 (可选) */
    tldr?: string;
}

export interface PaperLinks {
    /** PDF链接 */
    pdf: string;
    /** Arxiv链接 */
    arxiv: string;
    /** HTML页面链接 */
    html: string;
}

export interface PaperAnalysis {
    /** 分析摘要 */
    summary: string;
    /** 核心要点 */
    key_points: PaperDetails;
    /** 推荐理由 */
    recommendation_reason: string;
    /** 评分 */
    score: number;
}

export interface Paper {
    /** 论文ID */
    id: string;
    /** 标题 */
    title: string;
    /** 作者列表 */
    authors: string[];
    /** 发布日期 */
    date: string;
    /** 分类 (如 cs.LG) */
    category: string;
    /** 一句话总结 */
    tldr: string;
    /** 阅读建议 (如: 精读, 略读) */
    suggestion: string;
    /** 标签列表 */
    tags: string[];
    /** 详细信息 */
    details: PaperDetails;
    /** 相关链接 */
    links: PaperLinks;
    /** 引用数 */
    citationCount: number;
    /** 年份 */
    year: number;
    /** 是否已点赞 (前端状态) */
    isLiked?: boolean | null;
    /** 推荐理由 (个性化) */
    whyThisPaper?: string;
}
