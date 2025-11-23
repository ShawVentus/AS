# LLM 论文初筛功能集成与测试报告

本文档记录了将 LLM 集成到 `filter_papers` 功能中的实现逻辑、Prompt 设计及测试情况。

## 1. 功能实现逻辑

### 1.1 代码逻辑
在 `PaperService.filter_papers` 中，我们引入了 LLM 判别逻辑：
1.  **遍历论文**: 对传入的论文列表进行遍历。
2.  **跳过已处理**: 如果论文已有 `suggestion` (且不是 "Not Relevant")，则跳过 LLM 调用以节省 Token。
3.  **调用 LLM**: 使用 `LLMService.filter_paper` 接口，传入论文元数据（标题、摘要）和用户画像（Focus）。
4.  **处理结果**:
    - **相关 (Is Relevant)**: 更新数据库 `suggestion` 为 "Recommended: [Reason]"，保留在列表中。
    - **不相关 (Not Relevant)**: 更新数据库 `suggestion` 为 "Not Relevant: [Reason]"，`tldr` 设为 "N/A"，并从列表中移除。

### 1.2 Prompt 设计
使用了外置的 Prompt 模板 `backend/prompt/filter.md`：
```markdown
你是一个专业的学术论文筛选助手。
你的任务是根据用户的研究兴趣（Focus）和当前上下文（Context），判断一篇论文是否值得用户阅读。
...
返回格式要求：JSON { "is_relevant": true/false, ... }
```

## 2. 测试案例设计

我们创建了测试脚本 `backend/test/test_filter_llm.py`，使用真实的论文元数据进行验证。

### 2.1 测试数据 (Mistral 7B)
- **Title**: Mistral 7B
- **Abstract**: "We introduce Mistral 7B, a 7-billion-parameter language model engineered for superior performance and efficiency..."
- **Category**: cs.CL

### 2.2 测试场景 A: 相关用户 (LLM Researcher)
- **User Focus**: ["Large Language Models", "NLP", "LLM"]
- **预期结果**: ✅ **Passed**
- **LLM 预期判断**: 论文直接涉及 "Large Language Models"，与用户兴趣高度匹配。

### 2.3 测试场景 B: 不相关用户 (Biologist)
- **User Focus**: ["Biology", "Genetics", "Cell"]
- **预期结果**: ❌ **Filtered Out**
- **LLM 预期判断**: 论文属于计算机科学/NLP领域，与生物学无关。

## 3. 如何运行测试

您可以直接在终端运行以下命令来验证集成结果：

```bash
python backend/test/test_filter_llm.py
```

## 4. 数据流向图

```mermaid
graph LR
    A[Raw Paper] --> B{PaperService.filter_papers}
    B --> C[Load User Profile]
    B --> D[Load Prompt: filter.md]
    C & D --> E{LLM (Qwen)}
    E -->|Relevant| F[Update DB: Suggestion=Recommended]
    E -->|Not Relevant| G[Update DB: Suggestion=Not Relevant, tldr=N/A]
    F --> H[Return to Frontend]
    G --> I[Filter Out]
```
