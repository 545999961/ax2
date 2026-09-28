# 配置说明

顶层 CLI 只保留通用参数；数据集专属参数继续由
`vendor/research/eval_unified.py` 负责，通过可重复的 `--extra` 传入。

## research 通用参数

```text
research DATASET [DATASET ...]
  --n / --num-tasks N       选择 N 行
  --start-index I           从零开始的起始行（默认 0）
  --mode direct|refine_summary|return
  --model-name NAME         服务商模型标识
  --api-key-env ENV_NAME    保存 key 的环境变量名
  --base-url URL             OpenAI 兼容模型端点
  --data-path PATH          覆盖数据文件（只选择一个数据集时）
  --data-root PATH          准备好的数据根目录（默认 ./data）
  --save-path PATH          结果根目录
  --extra FLAG              传递一个评测器高级参数，可重复
```

例如选择第 100 到 119 行，并把并发数限制为 4：

```bash
python3 -m arex_v2 research BrowseComp \
  --start-index 100 --n 20 \
  --extra=--concurrency_limit=4
```

`--api-key-env` 的值是环境变量名，不是 key 本身。适配器会把该变量复制到
评测进程使用的内部环境变量，不会把密钥拼到命令预览中。`--model-name` 和
`--base-url` 不是凭据，可以出现在日志里。

## 环境变量

| 变量 | 用途 | 何时需要 |
| --- | --- | --- |
| `MODEL_API_KEY`（或 `--api-key-env` 指定的名字） | 模型 SDK | 真实模型调用 |
| `SERPER_API_KEY` | `search`、`google_scholar` | research 工具使用 Serper |
| `JINA_API_KEY` | `visit` | 私有或限流的 Jina 端点 |
| `SERPER_API_URL` | Serper 适配器 | 自定义 search 端点 |
| `SERPER_SCHOLAR_API_URL` | Serper Scholar 适配器 | 自定义 Scholar 端点 |
| `JINA_API_URL` | Jina 适配器 | 自定义 Reader 端点 |
| `MLE_BENCH` | MLE-bench Lite | prepare/run |
| `HF_TOKEN` | Hugging Face gated downloader | 获得许可后准备 HLE/GAIA |
| `AREX_TOKENIZER_PATH` | 本地 tokenizer | research token 计算 |
| 后端专用 key | Frontier/MLE 适配器 | 按所选后端要求 |

`configs/model.env.example` 只有变量名和占位符。真实值放在本地被忽略的文件
或 secret manager 中。

## 数据集路径

规范路径在 `data/` 下；不传 `--data-root` 时仍兼容
`vendor/research/datasets/` 中的旧路径。数据集配置定义在
`vendor/research/dataset_configs/*/config.json`：

| 数据集 | 默认输入 |
| --- | --- |
| BrowseComp | `data/BrowseComp/browse_comp_test_set.csv` |
| HLE | `data/HLE/text_items.jsonl` |
| GAIA-2023-validation-text-103 | `data/GAIA-2023-validation-text-103/standardized_data.jsonl` |
| DeepSearch-QA | `data/DeepSearch-QA/DSQA-full.csv` |

只选择一个数据集时可用 `--data-path`。多数据集运行传入单一路径会直接报错，
避免把同一个文件错误地应用到所有数据集。

## 高级评测参数

底层评测器支持以下类型的参数：

```bash
python3 -m arex_v2 research HLE --n 20 \
  --extra=--concurrency_limit=8 \
  --extra=--hle-max-completion-tokens=32768 \
  --extra=--disable-visit-fallback
```

完整列表：

```bash
python3 vendor/research/eval_unified.py --help
```

先用 `--dry-run` 检查。dry run 只打印构造出的子进程命令，不会访问模型、
Serper、Jina、judge 或 Docker。

## 结果和重跑

每个模型、mode 和任务范围使用独立的 `--save-path`。research 会创建
`<save-path>/<dataset>/.../result.json`。评测器默认跳过已经正确的题；明确要
全部重跑时使用 `--extra=--skip-existing-mode=none`。不要在同一个结果根目录混用
不同模型端点。
