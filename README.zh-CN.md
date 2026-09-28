<div align="center">

<img src="assets/arex-logo.svg" alt="AREX Benchmark" width="760" />

<p><strong>统一的 agent research、搜索、推理与基准评测平台</strong></p>

<a href="README.md">English</a> · <a href="docs/evaluation.zh-CN.md">评测说明</a> · <a href="docs/configuration.zh-CN.md">配置说明</a>

<br />

<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
<img src="https://img.shields.io/badge/Search-Serper-1D9BF0" alt="Serper search" />
<img src="https://img.shields.io/badge/Visit-Jina%20Reader-16A085" alt="Jina Reader visit" />
<img src="https://img.shields.io/badge/Data-on%20demand-F59E0B" alt="Data on demand" />

</div>

> **AREX Benchmark**（原 AREX v2）代表 **Agent Research & Evaluation eXchange**。Python 兼容模块仍然叫 `arex_v2`，已有命令继续有效。

AREX Benchmark 是 `self_evolving_v15` 的统一评测入口，把 research 基准、
Frontier-CS 算法题评测器和 MLE-bench Lite 放在同一个仓库中。大体积、加密
或受许可限制的数据不会提交到 Git。

- English README: [README.md](README.md)
- 详细配置：[docs/configuration.zh-CN.md](docs/configuration.zh-CN.md)
- 评测与计分：[docs/evaluation.zh-CN.md](docs/evaluation.zh-CN.md)
- 上游版本和许可证：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

## 📈 效果图

仓库内置当前项目的 benchmark 对比图，并以 SVG 保存，GitHub 页面上可以
保持清晰，也方便下载到报告中使用。

![AREX Benchmark results](assets/performance/arex-v2-benchmark-results.svg)

只有在 model endpoint、任务范围、工具和 judge 配置一致时，分数才具有可比性。
详见[评测和计分](docs/evaluation.zh-CN.md)。

目录组织参考了 MiroThinker 的使用顺序：安装、准备数据、选择基准、先做少量
smoke test，再查看官方评分产物。参考项目：[MiroThinker](https://github.com/MiroMindAI/MiroThinker)。

<details>
<summary>目录</summary>

- [效果图](#-效果图)
- [快速开始](#-快速开始)
- [配置](#-模型搜索和网页访问配置)
- [目录结构](#-目录结构)
- [运行后看什么](#-运行后看什么)

</details>

## 🚀 快速开始

### 1. 安装

需要 Python 3.10 或更高版本。按评测器安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[research]'       # BrowseComp/HLE/GAIA/DeepSearch-QA
# pip install -e '.[frontier]'     # Frontier-CS
# pip install -e '.[all]'          # 全部 Python 依赖
python3 -m arex_v2 doctor
```

### 2. 一键准备数据

```bash
python3 scripts/download_data.py --all
python3 scripts/download_data.py --list
# 等价的模块命令：
python3 -m arex_v2 download --all
```

该命令会把公开的 Frontier-CS 题面和测试数据下载到
`algorithmic/problems/`，并把核心 research 数据准备到 `data/`。BrowseComp
和 DeepSearch-QA 有公开发布文件；HLE、GAIA 需要先接受 Hugging Face 的 gated
条款并设置 `HF_TOKEN`。如果 gated 数据暂时不能下载，命令会报告缺失项，已
完成的下载不会丢失；用 `--list` 查看状态。

需要固定 Frontier 镜像并校验压缩包时：

```bash
python3 scripts/download_algorithmic.py \
  --url https://mirror.example/frontier-cs.tar.gz \
  --sha256 SHA256_HEX
```

### 3. 运行评测

research 的常用命令只需要数据集名称和任务数：

```bash
cp configs/model.env.example .env  # 先填写 model/key/tokenizer
set -a; source .env; set +a
python3 -m arex_v2 research BrowseComp --n 10 --dry-run
python3 -m arex_v2 research BrowseComp --n 10 \
  --model provider/model-name \
  --api-key-env MODEL_API_KEY \
  --base-url https://api.example.com/v1 \
  --save-path runs/browsecomp-10
```

`--n 10` 表示评测行号 `[0, 10)`；例如
`--start-index 100 --n 20` 表示 `[100, 120)`。多个数据集可以一次运行，
使用相同的范围：

```bash
python3 -m arex_v2 research BrowseComp HLE --n 5 --save-path runs/smoke
```

因为不同数据集的文件格式不同，`--data-path` 有意只允许选择一个数据集时
使用。多数据集运行时，把文件放在数据集配置列出的默认路径，或通过 `--extra`
传入评测器的高级参数，详见
[docs/configuration.zh-CN.md](docs/configuration.zh-CN.md)。

其他后端也通过同一个 CLI：

```bash
python3 -m arex_v2 algorithmic 1 path/to/solution.cpp --backend docker
MLE_BENCH=$HOME/mle-bench python3 -m arex_v2 mle leaf-classification --prepare
```

## ⚙️ 模型、搜索和网页访问配置

每个模型评测需要三个彼此独立的端点参数：

| 参数 | 示例 | 含义 |
| --- | --- | --- |
| model name | `provider/model-name` | 发给模型服务商的模型标识 |
| API key | `MODEL_API_KEY` | **保存密钥的环境变量名** |
| base URL | `https://api.example.com/v1` | 可选的 OpenAI 兼容端点 |

API key 的值只从环境变量读取，不会进入命令行参数、日志或仓库。可以复制
`configs/model.env.example` 到本地被忽略的文件来管理变量。评测器内部使用
`AREX_SDK_API_KEY`、`AREX_SDK_BASE_URL` 和 `AREX_MODEL_NAME`。

agent 还需要一个本地 tokenizer 来计算 token 数。请在示例文件中设置
`AREX_TOKENIZER_PATH`，或加上 `--tokenizer-path PATH`；它和服务端 model
endpoint 是两套独立配置。

research 工具使用固定协议：

```bash
export SERPER_API_KEY='...'   # search 和 Google Scholar
export JINA_API_KEY='...'     # visit；公开 r.jina.ai 可不填
```

`search` 使用 Serper，`visit` 使用 Jina Reader。可选端点变量是
`SERPER_API_URL`、`SERPER_SCHOLAR_API_URL` 和 `JINA_API_URL`。仓库不保存任何
key；dry run 只检查命令，不访问服务。

## 🗂️ 目录结构

```text
arex_v2/                  轻量 CLI 和后端适配器
vendor/research/          统一 research 评测器和数据集配置
vendor/frontier_cs/       Frontier-CS Python 源码快照
vendor/mle_lite/          MLE-bench Lite harness 快照
algorithmic/              Frontier 评测服务；题目按需下载
scripts/                  数据准备、下载和诊断脚本
configs/                  安全的配置示例（不含密钥）
reference/                为复现保留的原始 runner
docs/                     配置和各基准计分说明
assets/                   logo、图标和 benchmark 效果图
```

运行数据、结果目录、凭据和下载的题目都会被 Git 忽略。上游许可和版本记录在
`THIRD_PARTY_NOTICES.md`、`SNAPSHOT.txt`。

## ✅ 运行后看什么

research 会在 `--save-path` 下按数据集生成目录。逐题查看 `result.json`，
汇总 `score_result.score`，并同时保留 `status`、`official_scorer`、
`judge_raw` 和错误字段。Frontier 看 checker 的 case 分数，MLE-bench 看
host grader。每个任务的详细评测规则见
[docs/evaluation.zh-CN.md](docs/evaluation.zh-CN.md)。

## 🔧 常用命令

```bash
python3 -m arex_v2 list
python3 -m arex_v2 doctor
python3 scripts/download_data.py --list
python3 -m arex_v2 research BrowseComp --n 1 --dry-run
python3 -m arex_v2 download DeepSearch-QA --dry-run
```

不要提交基准数据、API key、模型输出或本地 `.env` 文件。
