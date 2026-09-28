# AREX Evaluation Suite

AREX 是 `self_evolving_v15` 使用的评测仓库。它把 research 基准及其评分器、
Frontier-CS 算法题 judge 和 MLE-bench Lite 放在同一个命令行入口中。数据集和
模型输出都保留在 Git 之外。

常用流程只有几步：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[research]'
cp configs/model.env.example .env
# 编辑 .env，再加载到当前 shell
set -a; source .env; set +a

python3 -m arex_v2 list
python3 -m arex_v2 download BrowseComp
python3 evaluate.py BrowseComp --n 1 --dry-run
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10
```

`evaluate.py 数据集` 和 `python3 -m arex_v2 evaluate 数据集` 完全等价。
数据集是唯一的位置参数；需要同时跑多个数据集时直接并列写出：

```bash
python3 evaluate.py BrowseComp HLE --n 5 --save-path runs/smoke
```

## 运行前配置

模型端点需要三项配置：

| 配置 | 示例 | 读取位置 |
| --- | --- | --- |
| model | `provider/model-name` | `AREX_MODEL_NAME` |
| API key | `secret-value` | `MODEL_API_KEY` 的值 |
| base URL | `https://api.example.com/v1` | `AREX_BASE_URL` |

命令接收的是 key 所在的**环境变量名**（默认是 `MODEL_API_KEY`），不会把
secret 放到参数中。research 评测还需要本地 tokenizer 统计 token，请设置
`AREX_TOKENIZER_PATH`。搜索和网页访问分别使用 `SERPER_API_KEY` 和
`JINA_API_KEY`；dry-run 不会访问这些服务。

`configs/model.env.example` 只提供变量名和占位符。真实值放在本地的 `.env`
中，该文件已被 Git 忽略。

## 数据集

用 `python3 -m arex_v2 list` 查看评测器接受的所有名称。下载命令可以准备下面
四个数据集：

| 数据集 | 准备方式 | 单题计分 |
| --- | --- | --- |
| BrowseComp | `python3 -m arex_v2 download BrowseComp` | BrowseComp 官方 judge |
| DeepSearch-QA | `python3 -m arex_v2 download DeepSearch-QA` | DeepSearch-QA autorater |
| HLE | 接受 Hugging Face 条款并设置 `HF_TOKEN`，再运行 `python3 -m arex_v2 download HLE` | HLE judge；`metrics.full_credit` |
| GAIA-2023-validation-text-103 | 设置 `HF_TOKEN`，再运行 `python3 -m arex_v2 download GAIA-2023-validation-text-103` | GAIA text judge |

评测器还包含 `HLE-NoTool`、`xBench-DeepSearch-2510`、WideSearch 各变体、
`DeepWideSearch`、`MoNaCo`、`DeepResearch-Bench` 和
`BrowseComp-Zh-official-en-prompt`。这些数据集有各自的许可或目录结构，请把
数据放到 `python3 -m arex_v2 download --list` 显示的路径，或在只选择一个数据集
时用 `--data-path` 指定文件。路径不存在时，命令会在启动评测器前直接报错。

需要把数据放在其他位置时使用 `--data-root PATH`。`--data-path PATH` 只允许
单数据集运行，避免把同一个文件误用于多个基准。

## 选择任务和查看结果

```bash
# 行号 [0, 20)
python3 evaluate.py BrowseComp --n 20

# 行号 [100, 120)
python3 evaluate.py BrowseComp --start-index 100 --n 20

# 只显示最终子进程命令，不调用模型、搜索、judge 或 Docker
python3 evaluate.py BrowseComp --n 1 --dry-run
```

每次运行会在 `--save-path` 下为每个数据集建立一个目录。research 基准逐题查看
`result.json`，汇总 `score_result.score` 前先检查 `status`、`official_scorer`、
`judge_raw` 和错误字段。请同时记录 model、端点、mode、任务范围和 Git commit；
不同配置得到的分数不能直接比较。

详细计分和结果示例见[评测说明](docs/evaluation.zh-CN.md)，高级参数见
[配置说明](docs/configuration.zh-CN.md)。英文说明在 [README.md](README.md)。

## 其他后端

同一个 CLI 也提供另外两个运行器：

```bash
python3 scripts/download_data.py --dataset algorithmic
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker

MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification
```

新 checkout 可以先运行 `python3 -m arex_v2 doctor`。目录保持简单：
`arex_v2/` 是 CLI 和适配器，`vendor/` 是上游评测器快照，`configs/` 是安全的
配置示例，`docs/` 说明数据准备和计分。上游版本与许可见
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和 [SNAPSHOT.txt](SNAPSHOT.txt)。
