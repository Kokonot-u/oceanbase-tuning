# Legacy Tests

本目录归档根目录旧 `tests/` 中不属于当前 B1/B2 主流程的测试。

当前 B1/B2 主测试入口为：

```bash
python3 -m pytest b1_b2/code/tests/test_week4_b1_b2.py -q
```

legacy 测试中包含 collector、db connection、B3、B4 等历史测试，后续应由对应模块维护。
