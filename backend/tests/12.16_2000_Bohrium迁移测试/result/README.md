# 测试结果目录

本目录用于存放玻尔API迁移测试的输出结果。

## 测试日志命名规范

- `test_log_YYYYMMDD_HHMM.txt`: 测试运行的完整日志
- `cost_comparison.csv`: 不同Provider的成本对比数据
- `error_log.txt`: 测试过程中遇到的错误记录

## 验收标准

✅ 测试通过标准：
1. 玻尔API连接成功，响应时间 < 5秒
2. 成本计算误差 < 0.000001 USD
3. 至少一个备用Provider可用
4. 论文筛选功能正常，结果格式正确

## 测试执行命令

```bash
cd /Users/mac/Desktop/AS/backend
conda activate arxivscout
python tests/12.16_2000_Bohrium迁移测试/test_bohrium_api.py
```
