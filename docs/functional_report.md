# Paper Scout Agent 功能测试与接口文档

本文档详细描述了 Paper Scout Agent 后端核心服务的功能、输入输出参数及测试情况。

## 1. PaperService (论文服务)

负责论文的获取、存储、检索和分析。

### 1.1 `get_papers`
- **功能**: 获取数据库中最新的论文列表。
- **输入**: 无
- **输出**: `List[Paper]` (论文对象列表)
- **测试情况**: ✅ 通过 (Unit Test & E2E)

### 1.2 `crawl_arxiv_new`
- **功能**: 触发 Scrapy 爬虫抓取最新 ArXiv 论文，并返回最新列表。
- **输入**: `limit: int` (默认 100)
- **输出**: `List[Paper]`
- **测试情况**: ✅ 通过 (Mocked Subprocess)

### 1.3 `filter_papers`
- **功能**: 根据用户画像过滤论文列表。**已集成 LLM**，使用外置 Prompt (`backend/prompt/filter.md`) 对论文标题和摘要进行语义匹配。
- **输入**: 
    - `papers`: `List[Paper]`
    - `user_profile`: `UserProfile`
- **输出**: `List[Paper]` (过滤后的列表)
- **测试情况**: ✅ 通过 (LLM Integration Test `backend/test/test_filter_llm.py`)

### 1.4 `analyze_paper`
- **功能**: 调用 LLM 对单篇论文进行深度分析，提取 TLDR、动机、方法等，并更新数据库。
- **输入**:
    - `paper`: `Paper`
    - `user_profile`: `UserProfile`
- **输出**: `PaperAnalysis` (分析结果对象，包含 summary, key_points, score 等)
- **测试情况**: ✅ 通过 (E2E Verification)

### 1.5 `get_recommendations`
- **功能**: 获取推荐的论文列表（过滤掉不相关的）。
- **输入**: 无
- **输出**: `List[Paper]`
- **测试情况**: ✅ 通过 (逻辑验证)

---

## 2. UserService (用户服务)

负责用户画像的管理、初始化和更新。

### 2.1 `get_profile`
- **功能**: 获取当前用户的完整画像。如果不存在则创建默认画像。
- **输入**: 无 (MVP模式下使用默认邮箱)
- **输出**: `UserProfile`
- **测试情况**: ✅ 通过 (User Flow Verification)

### 2.2 `initialize_profile`
- **功能**: 基于用户提交的基础信息初始化画像。
- **输入**: `user_info`: `UserInfo`
- **输出**: `UserProfile`
- **测试情况**: ✅ 通过 (逻辑验证)

### 2.3 `update_profile_nl`
- **功能**: 根据用户的自然语言反馈更新画像（如添加关注关键词）。
- **输入**:
    - `user_id`: `str`
    - `feedback_text`: `str`
- **输出**: `UserProfile` (更新后)
- **测试情况**: ✅ 通过 (User Flow Verification - Mocked Logic)

### 2.4 `update_profile_from_selection`
- **功能**: 根据用户对论文的 Like/Dislike 行为更新画像记忆。
- **输入**:
    - `user_id`: `str`
    - `feedbacks`: `List[UserFeedback]`
- **输出**: `UserProfile` (更新后)
- **测试情况**: ✅ 通过 (User Flow Verification)

---

## 3. ReportService (研报服务)

负责研报的生成、存储和邮件发送。

### 3.1 `generate_daily_report`
- **功能**: 聚合一组论文，调用 LLM 生成综述型研报，并保存到数据库。
- **输入**:
    - `papers`: `List[Paper]`
    - `user_profile`: `UserProfile`
- **输出**: `Report` (研报对象)
- **测试情况**: ✅ 通过 (Unit Test & Integration)

### 3.2 `send_email`
- **功能**: 将研报渲染为 HTML 并发送邮件给用户及配置的额外接收者。
- **输入**:
    - `report`: `Report`
    - `email`: `str` (主接收人)
- **输出**: `bool` (发送是否成功)
- **测试情况**: ✅ 通过 (Unit Test & Manual Config Check)

---

## 4. LLMService (大模型服务)

封装与 DashScope (Qwen) 的交互。

### 4.1 `filter_paper`
- **功能**: 判断论文是否与用户画像相关。
- **输入**: `paper: Dict`, `user_profile: str`
- **输出**: `Dict` (包含 is_relevant, score, reason)
- **测试情况**: ✅ 通过 (Unit Test)

### 4.2 `analyze_paper`
- **功能**: 深度分析论文内容。
- **输入**: `paper: Dict`, `user_profile: str`
- **输出**: `Dict` (包含 tldr, motivation, method, result, conclusion 等)
- **测试情况**: ✅ 通过 (Unit Test)

### 4.3 `generate_report`
- **功能**: 生成多篇论文的综述报告。
- **输入**: `papers: list`, `user_profile: str`
- **输出**: `Dict` (包含 title, summary, content)
- **测试情况**: ✅ 通过 (Unit Test)

---

## 测试总结

所有核心功能模块均已通过单元测试和端到端验证。
- **单元测试 (`backend/test/run_tests.py`)**: 覆盖了 LLM 调用、邮件发送、PaperService 基础逻辑。
- **E2E 验证 (`backend/test/verify_e2e.py`)**: 验证了从数据插入 -> LLM 分析 -> 数据回写的完整链路。
- **用户流验证 (`backend/test/verify_user_flow.py`)**: 验证了用户画像的获取、自然语言更新和行为反馈更新。
