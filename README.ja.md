# AnimeVoiceTutor

**ローカル環境を中心とした日本語会話練習アプリ**。AI 会話、任意の音声認識、追加可能なキャラクターボイスに対応しています。

[English](README.md) | [简体中文](README.zh-CN.md) | **日本語**

AnimeVoiceTutor は、ブラウザーで動作するセルフホスト型の日本語練習アプリです。キャラクターに依存しない Core で文章の会話や添削を行い、必要に応じて ASR と音声合成を追加できます。AI API の利用権や API キーは付属しません。

## 主な機能

- 利用者が設定した OpenAI または DeepSeek API による日本語会話。
- 表現の添削、送信済みメッセージの編集、文脈を保った会話の継続。
- 会話履歴、自動タイトル、ピン留め。
- 任意のローカル Qwen3-ASR による日本語音声入力。
- GPT-SoVITS と互換キャラクターパックによる任意の音声合成・再生。
- 日本語、英語、簡体中国語の UI。
- 標準状態では時間帯に応じた中立的なあいさつ。立ち絵、アニメーション、専用のあいさつと音声は追加パックで提供。

## Core と追加ダウンロード

| コンポーネント | Core ZIP に含まれるか | 備考 |
| --- | --- | --- |
| Web アプリと Windows 起動スクリプト | はい | 音声モデルなしでも起動可能 |
| 依存関係・セットアップ・テスト | はい | Python 等の取得は別途必要 |
| Qwen3-ASR モデル | いいえ | 任意でダウンロード |
| GPT-SoVITS 推論エンジン | いいえ | 別途導入または既存環境を参照 |
| キャラクター画像・音声重み・録音 | いいえ | 権利を確認した ZIP を追加 |
| AI API キー | いいえ | 利用者が設定 |

Core ZIP は**ソースコードと起動スクリプト**であり、単体の `.exe` や音声モデル一式ではありません。キャラクターパックを入れていない Core は、特定のキャラクターの声では話しません。

## Windows でのクイックスタート

1. [GitHub Releases](../../releases) から Core ソース ZIP をダウンロードするか、リポジトリをクローンし、別のフォルダーに展開します。
2. **`Setup AnimeVoiceTutor.cmd`** で Web 環境を導入します。**`Quick Setup.cmd`** から Web / ASR / TTS を個別に選択することもできます。
3. **`Start AnimeVoiceTutor.cmd`** を実行します。既定の URL は `http://127.0.0.1:8767` です。
4. **設定**で AI プロバイダーと API キーを登録します。
5. アプリの終了機能、または **`Stop AnimeVoiceTutor.cmd`** を使用します。

ASR やキャラクターモデルがなくても Web UI は起動できます。Quick Setup は Python 環境と依存パッケージを導入しますが、ASR モデル、GPT-SoVITS エンジン、キャラクター素材、FFmpeg は自動取得しません。

**動作環境：** Windows x64、PowerShell 5.1 以降。GPU を利用する音声機能には対応 NVIDIA ドライバー、CUDA/PyTorch、FFmpeg/ffprobe が必要です。提供する環境レシピは Web Python 3.11、ASR Python 3.12、TTS Python 3.10 を対象としています。詳細は[インストールガイド](docs/INSTALLATION.md)をご覧ください。

## 任意の音声機能とキャラクターパック

音声入力には ASR 環境を導入して **`Download ASR Model.cmd`** を実行してください。

キャラクターボイスには、互換 GPT-SoVITS-v5 エンジンと Python 環境を別途用意し、**設定 → キャラクター → ZIP をインストール** から権利を確認したパックを導入します。完全な音声パックは学習済み重み、参照音声、推論設定を含みますが、エンジン自体は含みません。話者の重みを切り替えた場合は管理対象の TTS サービスを再起動してください。

インストールしただけで画像・音声・学習済み重みの再配布権が生じることはありません。信頼できないモデルは読み込まないでください。詳細は[キャラクターパック](docs/CHARACTER_PACKS.md)。

## 診断と開発

プロジェクトの PowerShell から実行します。

```powershell
& '.\Doctor AnimeVoiceTutor.cmd'
& '.\Verify Source.cmd'
& '.\Test AnimeVoiceTutor.cmd'
& '.\Test AnimeVoiceTutor.cmd' -Voice
```

最後の音声テストは設定済みの TTS と ASR を使用して WAV と文字起こしを確認しますが、話者の再現度や外部 AI API の動作までは保証しません。

開発環境を手動で設定する場合：

```powershell
python -m pip install -e ".[test]"
python -m pytest -q tests
```

pip の例は Web とテスト用の依存関係のみです。詳しくは[インストール](docs/INSTALLATION.md)と[テスト](docs/TESTING.md)をご覧ください。

## リポジトリ構成

- `voice_tutor/` — バックエンドとキャラクター管理
- `web/` — ブラウザー UI
- `services/` — ASR サービス
- `scripts/` — セットアップ、起動、診断、ソース出力
- `tools/` — キャラクターパック作成と導入
- `release/` — 公開ファイル一覧と依存関係の定義
- `tests/` — 回帰テスト
- `docs/` — 詳細ガイド

開発用ディレクトリから **`Build Public Source.cmd`** で公開ソース ZIP を生成できます。`release/public_source_files.txt` に記載されたファイルだけを出力し、ローカルの資格情報、モデル、仮想環境、会話履歴は含みません。GitHub の Web UI と GitHub Desktop による公開方法は[公開ガイド](docs/PUBLISHING.md)をご覧ください。

## ライセンス

アプリケーションコードは [MIT License](LICENSE) です。外部のモデル、ソフトウェア、録音、画像にはそれぞれの利用条件があります。Core にはキャラクターの画像、専用音声モデル、参照録音、外部エンジンのソースコードを同梱していません。[第三者コンポーネント](THIRD_PARTY_NOTICES.md)と[セキュリティ](SECURITY.md)をご確認ください。
