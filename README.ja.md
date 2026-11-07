# AnimeVoiceTutor

**AIとの会話にアニメキャラクターならではの声を。より自然なキャラクターとの対話を楽しもう。**

[English](README.md) | [简体中文](README.zh-CN.md) | 日本語

AnimeVoiceTutor は、**キャラクターボイスを追加できる、オープンソースのセルフホスト型 AI キャラクター会話アプリ**です。キャラクター専用の音声パックを導入すると、テキストやマイクで AI キャラクターと会話し、そのキャラクターの合成音声で返答を聞くことができます。AI サービスの設定に加え、Qwen3-ASR によるローカル音声認識と GPT-SoVITS による音声合成に対応しています。

## 主な機能

- **キャラクターボイスパック：** AnimeVoiceTutor 専用 ZIP をダウンロード・導入し、キャラクターを切り替え。
- **AI 会話：** 対応する AI サービスと自分の API キーを設定して会話。
- **音声チャット：** マイク入力、ローカル音声認識、キャラクターボイスによる返答。
- **キャラクター画面：** 立ち絵、挨拶、会話履歴、多言語 UI。
- **ローカル実行：** Web・ASR・TTS を自分の PC で動作。
- **3 言語対応：** 日本語、英語、簡体字中国語。

## インストールと起動（Windows）

1. [GitHub Releases](https://github.com/Bocch1/AnimeVoiceTutor/releases) から **`AnimeVoiceTutor_Core_v0.13.1.zip`** をダウンロードし、書き込み可能なフォルダーにすべて展開します。
2. **`First Run Setup.cmd`** をダブルクリックし、**音声環境をインストールして「環境診断」で確認します**。言語メニューの表示名は常に **Language** です。既存のモデルやエンジンを使う場合は**詳細設定**を開きます。
3. **Release の Assets** から **AnimeVoiceTutor 専用キャラクター ZIP**（公開されている場合）をダウンロードし、**First Run のステップ 2** で導入します。ダウンロード済みの ZIP を選択したり、後から Web UI で導入したりすることもできます。
4. **`Start AnimeVoiceTutor.cmd`** をダブルクリックして起動します。**設定**で自分の AI サービスを登録して会話を始めます。終了時は Web UI の **アプリを終了** を使い、必要な場合だけ `Stop AnimeVoiceTutor.cmd` を使います。

**キャラクターパックは AnimeVoiceTutor 専用形式です。** 単体の `.pth` ファイルは完全なキャラクターパックではないため、そのまま導入できません。音声を利用するにはキャラクター情報・参照音声・推論設定・対応するモデルファイルが必要です。Core ZIP に第三者のキャラクター音声や素材は含まれていません。

主な対象環境は **Windows 10/11 x64 と NVIDIA GPU** です。ハードウェア、ドライバー、システム構成によって互換性が異なる場合があります。初回の依存関係・モデルの取得にはインターネット接続が必要です。詳しくは [インストール](docs/INSTALLATION.md) を参照してください。

## 通常の使い方

| ダブルクリックするファイル | 用途 |
| --- | --- |
| `First Run Setup.cmd` | 音声環境のインストール・診断、キャラクター ZIP のダウンロードと導入 |
| `Start AnimeVoiceTutor.cmd` | コンソールを開いたままにせずアプリを起動 |
| `Stop AnimeVoiceTutor.cmd` | Web 画面から終了できない場合に管理対象サービスを停止 |

通常の操作に PowerShell コマンドは不要です。開発・診断用ツールは [`advanced/`](advanced/) にあります。CMD ファイル名に空白があっても問題ありません。

## ローカルパッケージの保存先

```text
packages/
  updates/       AnimeVoiceTutor_Core_v0.13.1.zip
  characters/    AnimeVoiceTutor_Character_<id>_v<version>.zip
```

導入されたキャラクター ZIP は `packages/characters/` に保存され、実際のモデルは `data/character_packs/` に置かれます。これらのローカルファイルは公開 Core ZIP に含まれません。詳しくは [ローカル ZIP](docs/LOCAL_PACKAGES.md) を参照してください。

## ドキュメント

[インストール](docs/INSTALLATION.md) · [キャラクターパック形式](docs/CHARACTER_PACKS.md) · [ローカル ZIP](docs/LOCAL_PACKAGES.md) · [テスト](docs/TESTING.md) · [公開](docs/PUBLISHING.md)

## 非公式ファンプロジェクトと権利について

AnimeVoiceTutor は、**非営利目的で開発された独立した非公式ファンプロジェクト**です。アニメ制作会社、出版社、キャラクターの権利者、声優などとは提携・協賛関係がなく、公式の承認も受けていません。原作キャラクター、イラスト、音声収録、商標その他の第三者素材に関する権利は、それぞれの権利者に帰属します。

アプリ独自の**ソースコードには MIT ライセンス**が適用されますが、第三者のキャラクターや音声素材の利用・再配布を認めるものではありません。また、MIT ライセンス自体は商用利用を禁止しません。権利に関するご連絡は [GitHub リポジトリ](https://github.com/Bocch1/AnimeVoiceTutor/issues) までお願いします。正当な申し立ては速やかに確認し、必要に応じて該当素材を削除します。**削除要請への対応方針は、第三者素材の配布許可に代わるものではありません。** [第三者コンテンツについて](THIRD_PARTY_NOTICES.md)・[セキュリティ](SECURITY.md) もご覧ください。
