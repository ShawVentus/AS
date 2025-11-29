import { addDays, format, subDays } from 'date-fns';
import type { UserProfile, Paper, Report } from '../types';

export const USER_PROFILE: UserProfile = {
    info: {
        name: "Scholar_X",
        email: "student@uni.edu.cn",
        avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix",
        nickname: "Scholar_X"
    },
    focus: {
        category: ["cs.LG", "cs.AI"],
        keywords: ["LLM", "RAG", "Agent"],
        authors: ["Yann LeCun", "Geoffrey Hinton"],
        institutions: ["DeepMind", "OpenAI"]
    },
    context: {
        currentTask: "Research on RAG optimization",
        futureGoal: "Publish a top-tier paper",
        stage: "phd1",
        preferences: "寻找灵感, 跟进前沿",
        learningMode: 'basic'
    },
    memory: {
        readPapers: [],
        dislikedPapers: []
    }
};

export const MOCK_PAPERS: Paper[] = [
    {
        meta: {
            id: "p1",
            title: "MedAgent: Large Language Models as Generalists for Medical Consulting",
            authors: ["Xiangru Tang", "Anni Zou", "Junxian He"],
            published_date: "2025-10-24",
            category: ["cs.LG"],
            abstract: "Recent advancements in Large Language Models (LLMs) have shown promise in specialized medical tasks...",
            links: { pdf: "#", arxiv: "#", html: "#" },
        },
        analysis: {
            tldr: "提出基于LLM的医疗通用咨询Agent框架，显著提升诊断准确率。",
            tags: { "LLM": "LLM", "Medical": "Medical", "Agent": "Agent" },
            motivation: "现有医疗LLM专注单一任务，缺乏通用推理能力。",
            method: "Few-shot Prompting + RAG构建专家知识库。",
            result: "MedQA数据集SOTA，准确率提升15%。",
            conclusion: "LLM具备医疗通才潜力，需更好知识对齐。",
        },
        user_state: {
            paper_id: "p1",
            user_id: "student@uni.edu.cn",
            relevance_score: 0.95,
            why_this_paper: "契合您关注的 'LLM' 与 'Medical' 交叉领域，且作者 'Junxian He' 在您的关注列表中。",
            accepted: true,
            user_accepted: true,
            user_liked: null,
        }
    },
    {
        meta: {
            id: "p2",
            title: "Chain-of-Verification Reduces Hallucination in Large Language Models",
            authors: ["Shehzaad Dhuliawala", "Jason Weston"],
            published_date: "2025-10-23",
            category: ["cs.AI"],
            abstract: "Large Language Models (LLMs) often hallucinate plausible but incorrect facts...",
            links: { pdf: "#", arxiv: "#", html: "#" },
        },
        analysis: {
            tldr: "通过自我验证链机制，减少生成长文本时的幻觉。",
            tags: { "Hallucination": "Hallucination", "CoT": "CoT" },
            motivation: "幻觉阻碍LLM在严肃场景落地。",
            method: "CoVe: 生成 -> 验证 -> 修正。",
            result: "幻觉率降低30%。",
            conclusion: "自我验证有效且无需额外数据。",
        },
        user_state: {
            paper_id: "p2",
            user_id: "student@uni.edu.cn",
            relevance_score: 0.88,
            why_this_paper: "针对您关注的 'RAG' 和 'Agent' 可靠性问题，提供了通用的幻觉消除思路。",
            accepted: true,
            user_accepted: true,
            user_liked: null,
        }
    },
    {
        meta: {
            id: "p3",
            title: "DeepSeeker: An Efficient Agent for Academic Paper Screening",
            authors: ["Team A"],
            published_date: "2025-10-22",
            category: ["cs.IR"],
            abstract: "We present DeepSeeker, a tool designed to help researchers...",
            links: { pdf: "#", arxiv: "#", html: "#" },
        },
        analysis: {
            tldr: "用于快速筛选海量论文的轻量级Agent。",
            tags: { "Agent": "Agent", "Tool": "Tool" },
            motivation: "海量论文筛选效率低。",
            method: "BERT分类器 + 规则引擎。",
            result: "速度提升10倍。",
            conclusion: "适合初筛。",
        },
        user_state: {
            paper_id: "p3",
            user_id: "student@uni.edu.cn",
            relevance_score: 0.75,
            why_this_paper: "与您当前的 '开发论文查询Agent' 任务直接相关，可作为竞品分析参考。",
            accepted: false,
            user_accepted: false,
            user_liked: false,
        }
    }
];

export const MOCK_REPORTS: Report[] = [
    {
        id: "r1",
        title: "2025/10 W4 - 医疗Agent前沿进展",
        date: "2025-10-25",
        summary: "关注LLM医疗诊断通用性及幻觉消除技术。",
        content: [
            {
                text: "在医疗咨询领域，如何让大模型具备全科医生的能力是一个研究热点。最新的研究提出了MedAgent框架，通过结合检索增强生成技术，显著提升了诊断的准确性。",
                refIds: ["p1"]
            },
            {
                text: "然而，模型的幻觉问题依然严峻。针对这一问题，有学者提出了Chain-of-Verification (CoVe) 机制，通过让模型自我验证生成的内容，有效降低了错误率。同时，DeepSeeker等工具的出现也为筛选此类论文提供了便利。",
                refIds: ["p2", "p3"]
            }
        ]
    }
];

export const HEATMAP_DATA = Array.from({ length: 365 }, (_, i) => {
    const date = subDays(new Date(), i);
    return {
        date: format(date, 'yyyy-MM-dd'),
        count: Math.floor(Math.random() * 5),
    };
}).reverse();
