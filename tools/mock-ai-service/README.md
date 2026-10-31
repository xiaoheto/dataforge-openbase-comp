# Mock AI Service

公开 `ai_function_enhancement` 测试把 Endpoint 固定指向 `0.0.0.0:8000`，但比赛仓库没有提供该服务。本目录提供一个本地实现，让公开测试可以离线复现。

## 用法

```bash
python3 tools/mock-ai-service/mock_ai_service.py 8000
```

服务只依赖 Python 3 标准库，无需安装任何包。启动后保持前台运行，另开终端执行测试。

## 实现的端点

| 端点 | Provider | seekdb 读取的字段 |
| --- | --- | --- |
| `/compatible-mode/v1/chat/completions` | OpenAI | `$.choices[0].message.content` |
| `/compatible-mode/v1/embeddings` | OpenAI | `$.data[*].embedding` |
| `/api/generate` | Ollama | `$.response` |
| `/api/embed` | Ollama | `$.embeddings` |
| `/v1/rerank` | SiliconFlow | `$.results[*]` 的 `index` 与 `relevance_score` |

字段命名与 `src/sql/engine/expr/ob_expr_ai/ob_ai_func_utils.cpp` 中各 Provider 的 `parse_output()` 保持一致。Embedding 维度取请求中的 `dimensions`，缺省为 4。

## 回显模式

默认情况下 completion 返回固定文本，无法观察模板替换后的实际内容。设置环境变量后，completion 会把收到的 prompt 原样返回：

```bash
MOCK_AI_ECHO_PROMPT=1 python3 tools/mock-ai-service/mock_ai_service.py 8000
```

该开关只影响 completion 的响应文本，默认关闭，因此不影响已有测试的预期结果。开启后可以用 `ai_complete(...)` 的返回值直接断言替换后的 prompt。

## 边界

该服务不调用真实模型，所有响应都是确定性的、与输入内容无关的占位结果。它只能验证请求构造、响应解析和错误处理路径，不能替代比赛隐藏测试使用的官方服务。正式评分以官方服务为准。
