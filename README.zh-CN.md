# AREX-2 评测套件

AREX-2 是 `self_evolving_v15` 使用的评测仓库，统一放置 research、Frontier-CS 算法题和 MLE-bench Lite 三条评测线。数据集、模型输出和密钥不进 Git，仓库只保留评测器、数据集协议和可复现命令。

- 🌐 [项目主页](https://545999961.github.io/ax2/) — 研究概览和 benchmark 结果。
- 📚 [评测指南](data/README.md) — 数据准备、prompt 和各数据集评分方式。
- 🧪 [实验说明](scripts/README.md) — 运行配置和实验记录。
- 🇬🇧 [English](README.md) — English installation and evaluation guide.

## 目录

```text
evaluation/   CLI、评测适配器和固定版本的评测器
data/         数据集配置、准备清单和逐数据集说明
assets/       benchmark PDF/SVG、logo 和项目主页
scripts/      下载脚本、运行配置和算法题实验
evaluate.py   选择 research 数据集的根目录快捷入口
```

每个数据集的 `config.json`、`prompt.py`、`judge_local.py` 和 `judge_offical.py` 都在 `data/` 下，评测输入、评分器、指标和运行命令见 [data/README.md](data/README.md)。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[research]'   # research
# pip install -e '.[frontier]' # Frontier-CS
# pip install -e '.[all]'      # 全部依赖
python3 evaluate.py doctor
```

## Research 评测

先将[环境变量模板](scripts/configs/model.env.example)复制为 `.env`，填入模型、tokenizer、
外部 judge 和工具服务配置，再加载一次：

```bash
cp scripts/configs/model.env.example .env
# 编辑 .env 后执行：
set -a; source .env; set +a
```

```bash
python3 evaluate.py list
python3 evaluate.py BrowseComp --n 1 --dry-run
python3 evaluate.py BrowseComp --n 10 --save-path runs/browsecomp-10
python3 evaluate.py HLE --start-index 100 --n 20
```

外层只需要选择数据集，程序会自动找到对应配置、数据路径、prompt、loader 和 scorer。默认数据目录是 `data/files/`，也可以使用 `--data-root` 或单数据集的 `--data-path`。

直接选择 BrowseComp、GAIA、HLE 或 DeepSearch-QA 时，会自动使用
`refine-equal` profile：1 并发、10 轮、每轮最多 300 次调用、总计最多 1500 次调用，
并启用 confidence tiered review。四个数据集使用同一套 thinking、采样、token 和 retry
参数；unified backend 的 summary 使用推理模型，HLE 的 0724 solver 也使用该模型，
上下文和 review 调用由适配器负责；judge 由外部指定：

```bash
export MODEL_API_KEY=...
export JUDGE_API_KEY=...
python3 evaluate.py BrowseComp --n 10 \
  --model YOUR_MODEL --base-url http://model.example/v1 \
  --tokenizer-path /path/to/tokenizer \
  --judge-model YOUR_JUDGE --judge-base-url http://judge.example/v1 \
  --judge-api-key-env JUDGE_API_KEY \
  --save-path runs/browsecomp-10
```

完整参数见[配置说明](evaluation/docs/configuration.zh-CN.md#四个核心数据集的默认参数)。
`--profile default` 可以关闭这组 profile；`--dry-run` 会打印展开后的完整命令，不会调用服务。

有下载配方的数据集：

```bash
python3 evaluate.py download BrowseComp
python3 evaluate.py download DeepSearch-QA
python3 evaluate.py download HLE                 # 需要 HF_TOKEN 和访问权限
python3 evaluate.py download GAIA-2023-validation-text-103  # 需要 HF_TOKEN
python3 evaluate.py download --list
```

## Frontier-CS 算法题

评测器源码在 `evaluation/algorithmic/`，题目和运行结果在 `data/algorithmic/`：

```bash
python3 evaluate.py download algorithmic
python3 evaluate.py algorithmic 1 path/to/solution.cpp --backend docker
```

协议和 `scoreRatio` / `scoreRatioUnbounded` 的含义见 [data/algorithmic/README.md](data/algorithmic/README.md)。

## MLE-bench Lite

```bash
MLE_BENCH=$HOME/mle-bench python3 evaluate.py mle leaf-classification --prepare
MLE_BENCH=$HOME/mle-bench python3 evaluate.py mle leaf-classification
MLE_BENCH=$HOME/mle-bench \
  bash evaluation/mle_lite/scripts/grade.sh runs/<run-dir> leaf-classification
```

最终分数以 host grader 的 `grade.log` 为准。

## 结果图

![AREX benchmark results](assets/performance/arex-v2-benchmark-results.svg)
