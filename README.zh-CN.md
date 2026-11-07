# AnimeVoiceTutor

**本地优先的日语会话练习工具**，支持 AI 对话、可选语音识别，以及独立安装的角色语音包。

[English](README.md) | **简体中文** | [日本語](README.ja.md)

AnimeVoiceTutor 是一款自托管的浏览器应用，用于日语会话练习和表达纠正。基础版（Core）不绑定任何动漫人物，可以进行文字对话；需要语音输入、语音合成或人物形象时，再分别安装相应的运行环境和资源。应用不提供托管的 AI 服务或预置 API Key。

## 功能

- 连接用户自行配置的 OpenAI 或 DeepSeek API，进行日语会话。
- 查看表达纠正、编辑已发送消息，并结合上下文继续对话。
- 保存会话、自动生成标题及置顶常用会话。
- 通过可选的本地 Qwen3-ASR 进行日语语音输入。
- 使用可选的 GPT-SoVITS 和兼容角色包合成、播放日语语音。
- 提供简体中文、英语及日语界面。
- 默认使用中性的时间问候页面；人物立绘、动效、专属问候和声音由独立角色包提供。

## 下载内容

| 组件 | Core 源码包内是否包含 | 说明 |
| --- | --- | --- |
| 网页程序与 Windows 启动脚本 | 是 | 无语音模型也可启动 |
| 依赖配置、安装脚本和测试 | 是 | 安装时仍需下载 Python/依赖 |
| Qwen3-ASR 模型 | 否 | 按需单独下载 |
| GPT-SoVITS 推理引擎 | 否 | 单独安装或关联已有引擎 |
| 人物素材、语音权重和录音 | 否 | 按授权安装可选角色 ZIP |
| AI 服务商账号和 API Key | 否 | 用户自行配置 |

**Core ZIP 是源码和启动脚本，不是免安装的 `.exe`，也不是离线语音整合包。** 未安装角色包时，Core 不具备专属人物语音。

## Windows 快速开始

1. 从 [GitHub Releases](../../releases) 下载 Core 源码 ZIP，或克隆仓库；解压到独立文件夹。
2. 双击 **`Setup AnimeVoiceTutor.cmd`** 安装网页运行环境；也可以使用 **`Quick Setup.cmd`** 按需选择 Web、ASR、TTS 环境。
3. 双击 **`Start AnimeVoiceTutor.cmd`**，默认打开 `http://127.0.0.1:8767`。
4. 在**设置**中填写 AI 服务商和 API Key，才能进行在线 AI 对话。
5. 从网页退出，或运行 **`Stop AnimeVoiceTutor.cmd`**。

没有 ASR 模型、人物资源或 TTS 也能启动网页。Quick Setup **只安装 Python 及依赖**，不自动下载 ASR 模型、GPT-SoVITS 引擎、人物资源或 FFmpeg。

**系统要求：**Windows x64、PowerShell 5.1 或更新版本。GPU 语音功能需要兼容的 NVIDIA 驱动、CUDA/PyTorch 及 FFmpeg/ffprobe。提供的锁定环境分别采用 Python 3.11（Web）、3.12（ASR）、3.10（TTS）。详细要求见[安装指南](docs/INSTALLATION.md)。

## 可选语音与角色包

日语语音输入：安装 ASR 环境后运行 **`Download ASR Model.cmd`**，按需下载 Qwen3-ASR 模型。

人物语音：单独安装兼容的 GPT-SoVITS-v5 引擎及其运行环境，再通过 **设置 → 角色 → 安装 ZIP** 导入有权使用的角色包。完整语音角色包应包含人物权重、参考音频和推理参数，但**不包含推理引擎本身**。切换不同权重时需要重新启动受管理的 TTS 服务。

角色包可以独立安装、切换；安装本身不等于取得人物图片、配音素材或模型权重的公开分发权。不要安装来源不可信的模型文件。详见[角色包说明](docs/CHARACTER_PACKS.md)。

## 诊断和测试

在项目目录的 PowerShell 中运行：

```powershell
& '.\Doctor AnimeVoiceTutor.cmd'       # 检查本地依赖与模型路径
& '.\Verify Source.cmd'                # 检查公开源码与回归测试
& '.\Test AnimeVoiceTutor.cmd'         # 检查运行中的网页服务
& '.\Test AnimeVoiceTutor.cmd' -Voice  # 需要已配置的 TTS 和 ASR
```

语音测试会生成 WAV 并让 ASR 识别，但不能证明人物音色相似度，也不会验证在线 AI 服务商。可在设置中单独测试服务商连接。

开发者可选择自己的 Python 环境：

```powershell
python -m pip install -e ".[test]"
python -m pytest -q tests
```

上述 pip 安装仅覆盖 Web 与测试依赖，不会安装 GPU 推理引擎或模型。更多内容见[安装](docs/INSTALLATION.md)和[测试](docs/TESTING.md)。

## 项目结构

- `voice_tutor/`：后端和角色包机制
- `web/`：浏览器界面
- `services/`：ASR 服务
- `scripts/`：安装、启动、诊断与公开源码构建
- `tools/`：角色包制作、导入及本地工具
- `release/`：公开文件清单及依赖版本
- `tests/`：自动化回归测试
- `docs/`：安装、角色、测试和发布文档

维护者运行 **`Build Public Source.cmd`** 即可从开发目录生成公开源码 ZIP。构建器仅包含 `release/public_source_files.txt` 中的文件，不包括本地模型、凭据、缓存及虚拟环境。通过 GitHub 网页发布 ZIP 或使用 GitHub Desktop 更新仓库，参见[发布指南](docs/PUBLISHING.md)。

## 许可证与第三方素材

应用源码采用 [MIT 许可证](LICENSE)。第三方依赖、模型、语音和人物素材受各自的条款约束。Core 不分发人物立绘、角色权重、参考音频或第三方引擎源码。详见[第三方说明](THIRD_PARTY_NOTICES.md)及[安全说明](SECURITY.md)。
