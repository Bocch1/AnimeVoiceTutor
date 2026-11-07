# AnimeVoiceTutor

**ローカル音声認識と追加キャラクター音声に対応した、日本語会話練習アプリです。**

[English](README.md) | [简体中文](README.zh-CN.md) | 日本語

音声認識には Qwen3-ASR、音声合成には GPT-SoVITS を使用します。AI 会話には、利用者自身が OpenAI / DeepSeek などの API キーを設定してください。Core ZIP に学習済みモデル、キャラクターの素材、API キーは含まれていません。

## 初回セットアップ（Windows）

1. GitHub Releases から **`AnimeVoiceTutor_Core_v0.13.1.zip`** をダウンロードし、ZIP 全体を書き込み可能なフォルダーに展開します。更新パッチの `payload` フォルダーから起動しないでください。
2. **`First Run Setup.cmd`** をダブルクリックします。言語メニューは常に **Language** と表示されます。ステップ 1 には **環境のインストール・環境診断・詳細設定** の 3 つがあります。既存の GPT-SoVITS / ASR を使う場合は詳細設定で選択できます。
3. ステップ 2 で GitHub Releases のキャラクター一覧を更新し、対象 ZIP を選択してダウンロード・導入します。信頼できるローカル ZIP の取り込みや、後から Web 画面での取り込みもできます。
4. **`Start AnimeVoiceTutor.cmd`** をダブルクリックしてアプリを起動します。設定画面で AI API キーを入力し、録音・会話・音声再生を確認してください。終了時はサイドバーの **アプリを終了** を使います。必要な場合だけ `Stop AnimeVoiceTutor.cmd` を使います。

通常の操作にコマンド入力は不要です。環境診断の成功は、キャラクターの TTS モデルが実際に読み込まれたことを意味しません。起動中は読み込みを待ち、失敗した場合はサービス状態を確認してください。

**動作対象：** Windows 10/11 x64 と CUDA 12.8 に対応する NVIDIA GPU / ドライバー。すべての PC での自動インストールを保証するものではありません。開発用 GPT-SoVITS には未公開のローカル変更があり、完全な再現性はまだ検証中です。

## ローカル ZIP の保存先

セットアップ時に次のフォルダーが自動作成されます。

```text
packages/
  updates/       AnimeVoiceTutor_Core_v0.13.1.zip、AnimeVoiceTutor_Update_v0.13.1.zip
  characters/    AnimeVoiceTutor_Character_<id>_v<version>.zip
```

導入済みキャラクター ZIP は `packages/characters` に保存されます。展開されたモデルは従来どおり `data/character_packs` に残ります。Core のビルド結果は `packages/updates` に保存されます。両フォルダーは Git の対象外で、公開 Core ZIP に含まれません。詳細は [Local packages](docs/LOCAL_PACKAGES.md) を参照してください。

## 通常使う 3 つの CMD

| ファイル | 操作 |
| --- | --- |
| `First Run Setup.cmd` | 環境のインストール・診断・キャラクターの導入 |
| `Start AnimeVoiceTutor.cmd` | コンソールを常時表示せずアプリを起動 |
| `Stop AnimeVoiceTutor.cmd` | 画面から終了できない場合の停止操作 |

**CMD ファイル名に空白があっても問題ありません。** 内部ではパスを引用符で囲んでいます。開発・診断用のツールは [`advanced/`](advanced/) にあります。

[インストール](docs/INSTALLATION.md) · [ZIP 保存先](docs/LOCAL_PACKAGES.md) · [キャラクターパック](docs/CHARACTER_PACKS.md) · [テスト](docs/TESTING.md) · [公開](docs/PUBLISHING.md)

**ライセンス：** Core ソースは MIT ですが、人物画像・音声・モデルなどの再配布には別の許可が必要です。削除依頼窓口だけでは再配布許可になりません。[Security](SECURITY.md) と [Third-party notices](THIRD_PARTY_NOTICES.md) を確認してください。
