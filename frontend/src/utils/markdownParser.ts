/**
 * 段落内容片段
 */
export interface ContentFragment {
    type: 'text' | 'ref-sentence';
    content: string;
    refIds?: string[];  // 当 type === 'ref-sentence' 时存在
}

/**
 * 解析后的段落
 */
export interface ParsedParagraph {
    type: 'heading' | 'paragraph' | 'list';
    level?: number;  // 标题级别 (1-6)
    fragments: ContentFragment[];
}

/**
 * 将文本按句子边界分割
 * 
 * Args:
 *   text: 待分割的文本
 * 
 * Returns:
 *   句子数组
 */
function splitSentences(text: string): string[] {
    // 匹配句号、问号、感叹号作为句子结束，保留标点符号
    // 使用正向预查 (?<=[。？！?!]) 确保标点符号留在句子中
    // 注意：这里简单处理，可能无法处理所有复杂情况（如引号内的标点）
    return text.split(/(?<=[。？！?!])\s*/).filter(s => s.trim().length > 0);
}

/**
 * 从句子中提取所有 <ref id="xxx"> 标签的 ID
 * 
 * Args:
 *   sentence: 句子文本
 * 
 * Returns:
 *   引用 ID 数组
 */
function extractRefsFromSentence(sentence: string): string[] {
    const refPattern = /<ref id="([^"]+)">/g;
    const ids: string[] = [];
    let match: RegExpExecArray | null;
    while ((match = refPattern.exec(sentence)) !== null) {
        let id = match[1].trim();
        // 兼容处理：如果 ID 以 'p' 开头（如 p2512.04207），去除 'p'
        if (id.startsWith('p')) {
            id = id.substring(1);
        }
        ids.push(id);
    }
    return ids;
}

/**
 * 移除文本中的 <ref> 标签，保留纯文本
 * 
 * Args:
 *   text: 包含 <ref> 标签的文本
 * 
 * Returns:
 *   清理后的纯文本
 */
function cleanRefTags(text: string): string {
    return text.replace(/<ref id="[^"]+">/g, '');
}

/**
 * 从文本中提取所有引用 ID (导出供外部使用)
 * 
 * Args:
 *   text: 包含引用标记的文本
 * 
 * Returns:
 *   引用 ID 数组
 */
export function extractRefIds(text: string): string[] {
    return extractRefsFromSentence(text);
}

/**
 * 解析单个文本行，识别引用标记并按句子分割
 * 
 * Args:
 *   text: 原始文本行
 * 
 * Returns:
 *   内容片段数组
 */
function parseLine(text: string): ContentFragment[] {
    const fragments: ContentFragment[] = [];

    // 1. 按句子分割
    const sentences = splitSentences(text);

    for (const sentence of sentences) {
        // 2. 提取引用 ID
        const refIds = extractRefsFromSentence(sentence);

        // 3. 清理标签获取纯文本，并移除标点符号前的空格
        const cleanText = cleanRefTags(sentence).replace(/\s+([。？！?!])/g, '$1');

        if (refIds.length > 0) {
            // 4. 如果有引用，创建 ref-sentence 片段
            fragments.push({
                type: 'ref-sentence',
                content: cleanText,
                refIds: refIds
            });
        } else {
            // 5. 否则创建普通文本片段
            fragments.push({
                type: 'text',
                content: cleanText
            });
        }
    }

    return fragments;
}

/**
 * 解析 Markdown 内容，识别引用标记
 * 
 * Args:
 *   markdown: Markdown 格式的报告内容
 * 
 * Returns:
 *   解析后的段落数组
 */
export function parseMarkdown(markdown: string): ParsedParagraph[] {
    if (!markdown) return [];

    const lines = markdown.split('\n');
    const parsed: ParsedParagraph[] = [];

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        // 标题
        if (trimmed.startsWith('#')) {
            const match = trimmed.match(/^(#+)\s+(.+)$/);
            if (match) {
                parsed.push({
                    type: 'heading',
                    level: match[1].length,
                    fragments: parseLine(match[2])
                });
                continue;
            }
        }

        // 列表
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            parsed.push({
                type: 'list',
                fragments: parseLine(trimmed.slice(2))
            });
            continue;
        }

        // 普通段落
        parsed.push({
            type: 'paragraph',
            fragments: parseLine(trimmed)
        });
    }

    return parsed;
}
