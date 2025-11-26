export interface PaperDetails {
    /** 研究动机 */
    motivation: string;
    /** 研究方法 */
    method: string;
    /** 实验结果 */
    result: string;
    /** 结论 */
    conclusion: string;
}

export interface PaperLinks {
    /** PDF链接 */
    pdf: string;
    /** Arxiv链接 */
    arxiv: string;
    /** HTML页面链接 */
    html: string;
}

export interface RawPaperMetadata {
    id: string;
    title: string;
    authors: string[];
    published_date: string;
    category: string[];
    abstract: string;
    links: PaperLinks;
    comment?: string;
}

export interface PaperAnalysis {
    tldr?: string;
    motivation?: string;
    method?: string;
    result?: string;
    conclusion?: string;
    tags: Record<string, string>; // Changed from string[] to Dict
}

export interface UserPaperState {
    paper_id: string;
    user_id: string;
    relevance_score: number;
    why_this_paper?: string;
    accepted: boolean;
    user_accepted: boolean;
    user_liked?: boolean | null;
    user_feedback?: string;
}

export interface PersonalizedPaper {
    meta: RawPaperMetadata;
    analysis?: PaperAnalysis;
    user_state?: UserPaperState;
}

// Alias for backward compatibility
export type Paper = PersonalizedPaper;
