# 配置说明

仓库包装器只保留通用参数；数据集专属参数继续由
`vendor/research/eval_unified.py` 处理，可以通过重复的 `--extra` 传入。

## 常用参数

```text
evaluate DATASET [DATASET ...]
  --n / --num-tasks N       评测行数
  --start-index I           从零开始的起始行（默认 0）
  --mode direct|refine_summary|return
  --model NAME              服务商模型标识
  --api-key-env ENV_NAME    保存 key 的环境变量名
  --base-url URL             OpenAI 兼容模型端点
  --data-path PATH           覆盖单个数据集的输入
  --data-root PATH           准备好的数据根目录（默认 ./data）
  --save-path PATH           结果根目录（默认 runs/<timestamp>）
  --concurrency N            最大并发题数（默认 4）
  --extra FLAG               评测器高级参数，可重复
```

例如：

```bash
python3 evaluate.py BrowseComp --start-index 100 --n 20 \
  --extra=--concurrency_limit=4
```

`--api-key-env` 的值是环境变量名，不是 secret。适配器会把该变量复制到评测器
的私有环境中，命令预览里不会出现它的值。`--model` 和 `--base-url` 不是凭据，
可以显示。

`--dry-run` 只显示最终子进程命令，不会访问模型、搜索服务、网页、judge 或 Docker。
真实运行前会检查所选数据路径是否存在。

## 环境变量

| 变量 | 用途 | 何时需要 |
| --- | --- | --- |
| `MODEL_API_KEY`（或 `--api-key-env` 指定的变量） | model SDK | 所有真实 research 评测 |
| `AREX_MODEL_NAME` | 默认 model | 所有真实 research 评测 |
| `AREX_BASE_URL` | 默认模型端点 | 自定义端点时 |
| `AREX_TOKENIZER_PATH` | 本地 token 统计 | unified research 数据集 |
| `SERPER_API_KEY` | `search`、`google_scholar` | research 工具 |
| `JINA_API_KEY` | `visit` | 私有或限流的 Jina |
| `HF_TOKEN` | Hugging Face 下载 | HLE、GAIA 准备 |
| `MLE_BENCH` | MLE-bench Lite | MLE prepare/run |

可选端点变量是 `SERPER_API_URL`、`SERPER_SCHOLAR_API_URL` 和
`JINA_API_URL`。真实值放在本地被忽略的 `.env` 或 secret manager 中。

## 数据路径

可下载数据集默认放在 `data/<dataset>/...`：

| 数据集 | 默认输入 |
| --- | --- |
| BrowseComp | `data/BrowseComp/browse_comp_test_set.csv` |
| DeepSearch-QA | `data/DeepSearch-QA/DSQA-full.csv` |
| HLE | `data/HLE/text_items.jsonl` |
| GAIA-2023-validation-text-103 | `data/GAIA-2023-validation-text-103/standardized_data.jsonl` |

不传 `--data-root` 时，`vendor/research/` 下匹配的旧文件仍会被接受。其他评测器
数据集使用 `vendor/research/dataset_configs/*/config.json` 里的路径，可以用
`python3 -m arex_v2 download --list` 查看。

多数据集运行传入 `--data-path` 会直接报错，避免把一个文件应用到所有数据集。

## 高级参数和重跑

底层评测器支持：

```bash
python3 evaluate.py HLE --n 20 \
  --extra=--hle-max-completion-tokens=32768 \
  --extra=--disable-visit-fallback
```

完整列表：

```bash
python3 vendor/research/eval_unified.py --help
```

每个 model、mode 和任务范围使用独立的 `--save-path`。评测器默认跳过已经正确的题；
明确重跑时使用 `--extra=--skip-existing-mode=none`。
