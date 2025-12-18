export interface UserInfo {
    /** 用户ID */
    id?: string;
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
    /** 是否接收邮件 */
    receive_email?: boolean;
}

export interface Focus {
    /** 关注领域列表 (arXiv Category) */
    category: string[];
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
    /** 研究偏好列表 (最多10条，每条最多200字符) */
    preferences: string[];
    /** 阶段 (可选) */
    stage?: string;
    /** 学习模式 (可选) */
    learningMode?: string;
}

export interface UserFeedback {
    /** 论文ID */
    paper_id: string;
    /** 动作类型: read | like | dislike */
    action_type: 'read' | 'like' | 'dislike';
    /** 原因 (可选) */
    reason?: string;
    /** 时间戳 */
    timestamp?: string;
}

export interface Memory {
    /** 用户历史提示词 */
    user_prompt: string[];
    /** 用户交互记录 */
    interactions: UserFeedback[];
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
    /** 是否已完成产品引导教程 */
    has_completed_tour?: boolean;
}

export interface NaturalLanguageInput {
    text: string;
    user_id: string;
}
