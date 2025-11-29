export interface UserInfo {
    /** 用户姓名 */
    name: string;
    /** 邮箱地址 */
    email: string;
    /** 头像URL */
    avatar: string;
    /** 昵称 */
    nickname: string;
    /** 角色 */
    role?: string;
}

export interface Focus {
    /** 关注领域列表 */
    domains: string[];
    /** 关注关键词列表 */
    keywords: string[];
    /** 关注作者列表 */
    authors: string[];
    /** 关注机构列表 */
    institutions: string[];
}

export interface Context {
    /** 当前任务 */
    currentTask: string;
    /** 未来目标 */
    futureGoal: string;
    /** 当前阶段 (如: 研一, 博士) */
    stage: string;
    /** 阅读目的 */
    purpose: string[];
    /** 学习模式: 基础模式 | 创新模式 */
    learningMode: 'basic' | 'innovation';
}

export interface Memory {
    /** 已读论文ID列表 */
    readPapers: string[];
    /** 不感兴趣论文ID列表 */
    dislikedPapers: string[];
}

export interface UserProfile {
    /** 基本信息 */
    info: UserInfo;
    /** 关注点 */
    focus: Focus;
    /** 上下文 */
    context: Context;
    /** 记忆/历史 */
    memory: Memory;
}

export interface UserFeedback {
    /** 论文ID */
    paper_id: string;
    /** 是否喜欢 */
    is_like: boolean;
    /** 原因 (可选) */
    reason?: string;
}

export interface NaturalLanguageInput {
    text: string;
    user_id: string;
}
