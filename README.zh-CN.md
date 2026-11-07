# AnimeVoiceTutor

**自托管日语对话练习工具，支持本地语音识别和独立安装的人物语音包。**

[English](README.md) | 简体中文 | [日本語](README.ja.md)

程序使用 Qwen3-ASR 识别语音、GPT-SoVITS 合成人物语音；AI 对话需在网页设置中填写自己的 OpenAI / DeepSeek 等受支持服务商 API Key。Core ZIP 不包含模型权重、人物素材或 API Key。

## 首次使用（Windows）

1. 从项目的 GitHub Releases 下载 **`AnimeVoiceTutor_Core_v0.13.1.zip`**，把整个 ZIP 解压到可写入的目录。不要进入增量补丁 ZIP 的 `payload` 目录运行安装器。
2. 双击 **`First Run Setup.cmd`**。语言切换入口始终显示为 **Language**（简体中文 / English / 日本語）。第一步只需使用 **安装环境、环境诊断、高级选项**：先点击安装；如果已经装过，可以直接诊断；高级选项可选本机已有 GPT-SoVITS 引擎或 ASR 模型。
3. 在第二步刷新 GitHub Releases 人物列表，选择角色 ZIP 并点击**下载并安装角色**；也可选择电脑里已有的可信 ZIP。后续还可以从 Web 设置中导入。
4. 双击 **`Start AnimeVoiceTutor.cmd`** 启动网页应用。在设置中填写自己的 AI API Key，进行日语录音、对话和实时语音播放。结束时点击网页侧边栏的**退出应用**；必要时可双击 `Stop AnimeVoiceTutor.cmd`。

**日常使用不需要控制台命令。** “环境诊断”检查基础环境是否完整，不等同于验证某个人物的权重已经加载。TTS 启动中应等待模型初始化；若一直失败，可在网页的“服务状态”中查看详情。

**当前目标平台**为 Windows 10/11 x64、兼容 CUDA 12.8 的 NVIDIA 显卡与驱动。首次下载依赖和模型需要网络，并不能保证所有电脑都可自动完成。尽管已固定 GPT-SoVITS 上游版本，你本机额外修改过的推理文件尚未制成正式兼容包，因此不能承诺所有电脑的音频结果完全相同。

## 本地安装包放在哪里？

首次安装窗口会在项目根目录自动创建：

```text
packages/
  updates/       AnimeVoiceTutor_Core_v0.13.1.zip、AnimeVoiceTutor_Update_v0.13.1.zip
  characters/    AnimeVoiceTutor_Character_<角色id>_v<版本>.zip
```

从 First Run 或网页成功导入的人物 ZIP 会自动保存一份到 `packages/characters`，方便备份和转移；实际解压并运行的模型仍在 `data/character_packs`，不会被移动。通过高级构建工具生成的 Core ZIP 默认放入 `packages/updates`。两个归档文件夹都被 Git 忽略，不会进入公开源码 ZIP。见 [本地文件夹与命名说明](docs/LOCAL_PACKAGES.md)。

## 根目录保留三个 CMD

| 双击文件 | 用途 |
| --- | --- |
| `First Run Setup.cmd` | 安装或诊断语音环境、下载导入人物 |
| `Start AnimeVoiceTutor.cmd` | 正常启动程序，无需一直打开控制台 |
| `Stop AnimeVoiceTutor.cmd` | 网页退出失败时停止本程序管理的服务 |

**CMD 文件名中有空格完全正常**，不必改名。脚本已经对带空格的调用路径加引号；旧的诊断、测试、手动安装与发布工具统一放在 [`advanced/`](advanced/)。

## 更多说明

[安装与诊断](docs/INSTALLATION.md) · [本地安装包归档](docs/LOCAL_PACKAGES.md) · [人物包格式](docs/CHARACTER_PACKS.md) · [测试说明](docs/TESTING.md) · [发布说明](docs/PUBLISHING.md)

**版权与安全：** Core 程序源代码采用 MIT 许可证，但第三方模型、人物立绘、声音权重和录音各有自己的许可。未经适当授权，不应公开发布相关人物包；“侵权联系删除”并不能代替授权。详见 [安全说明](SECURITY.md) 和 [第三方声明](THIRD_PARTY_NOTICES.md)。
