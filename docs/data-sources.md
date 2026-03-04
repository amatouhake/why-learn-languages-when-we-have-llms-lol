# HSK単語学習データセット：音声付きオープンリソース完全ガイド

**CC-CEDICTを除いた最有力候補は、語彙データとして `complete-hsk-vocabulary`（MIT / JSON）、音声データとして `audio-cmn`（CC-BY-SA / MP3 約8,596語）の組み合わせである。** この2つを軸に、TTS URLが付属する HuggingFace の `hsk-dataset`（CC-BY-4.0）、例文付きの `clem109/hsk-vocabulary`（MIT / JSON）を補完的に使うことで、個人学習用Webアプリに必要なデータをほぼすべてカバーできる。日本語訳を含むオープンデータセットは現時点で存在しないため、別途辞書データとのクロスリファレンスが必要になる。

---

## 最優先：語彙JSON＋音声MP3の黄金コンビ

### complete-hsk-vocabulary（語彙データの決定版）

- **URL**: https://github.com/drkameleon/complete-hsk-vocabulary
- **ライセンス**: MIT
- **形式**: JSON（`complete.json` / `complete.min.json` ＋ レベル別分割ファイル）
- **HSKカバー範囲**: **HSK 2.0（旧1〜6級）と HSK 3.0（新1〜9級）の両方を完全収録**
- **フィールド**: 簡体字(s)、繁体字、ピンイン、HSKレベル(l)（新旧両方）、頻度ランク(q)、品詞(p)、英語定義(m)、量詞(c)
- **単語数**: HSK 2.0 + 3.0 の全語彙（旧HSK約5,000語 ＋ 新HSK約11,000語）
- **日本語訳**: なし（英語のみ）
- **音声**: なし

GitHub上で**138スター**を獲得しており、HSK語彙データセットとしては最も包括的でメンテナンスも活発。GitHub Actionsでレベル別JSONファイルが自動生成される仕組みになっている。`wordlists/inclusive/` と `wordlists/exclusive/` のディレクトリ構造で、累積語彙リストと各級固有語彙リストの両方が取得できるため、**HSK1〜3級だけを抽出する用途にも最適**。定義データはCC-CEDICTに由来するが、クリーニングと構造化が施されており、そのまま使える品質である。

### audio-cmn（HSK語彙音声の決定版）

- **URL**: https://github.com/hugolpz/audio-cmn
- **ライセンス**: CC-BY-SA（ネイティブスピーカーChen Wang・Yue Tanの録音に基づく）
- **形式**: MP3（96k / 64k / 24k / 18k の4種類のビットレートで提供）
- **収録数**: **音節1,707件 ＋ HSK単語8,596件 ＝ 合計約10,303ファイル**
- **カバー範囲**: HSK 2000規格（2000年版公式リスト）のほぼ全語彙
- **命名規則**: 音節は `cmn-{声調付きピンイン}.mp3`、単語は `cmn-{漢字}.mp3`

元データはShtookaプロジェクト（SWAC Recorder）の高品質FLAC録音で、これをMP3に変換・最適化したもの。**ネイティブスピーカーによる実録音であり、TTS合成音声ではない**点が大きな強み。ビットレート別のディレクトリ構成のため、Webアプリでは64kまたは96kを使えばよい。HSK 2012版リストとの差分をチェックするスクリプト（`hsk-missing-audios.bash`）も同梱されており、欠落ファイルを特定できる。

この2つを組み合わせれば、漢字→ピンイン→英語定義→ネイティブ音声 のデータパイプラインがWebアプリ上で完成する。

---

## TTS URL付きで即座に使える HuggingFace データセット

- **名称**: willfliaw/hsk-dataset
- **URL**: https://huggingface.co/datasets/willfliaw/hsk-dataset
- **ライセンス**: **CC-BY-4.0**
- **形式**: CSV（619KB）/ Parquet（333KB）/ HuggingFace `datasets` ライブラリで直接ロード可能
- **フィールド**: `level`（HSK級）, `hanzi`, `pinyin`（声調なし）, `pinyin_tone`（声調符号付き）, `pinyin_num`（数字声調）, `english`, `pos`（品詞・中国語表記）, **`tts_url`**
- **単語数**: 約5,000語（HSK 2.0 の1〜6級）
- **音声**: 各エントリに `https://api.wohuimandarin.com/nls/tts?text=...` 形式のTTS URLが付属

**音声データを自前でホスティングしたくない場合に最適**。各単語のTTS URLをそのまま `<audio>` タグの `src` に指定すれば音声再生が可能になる（ただし外部APIへの依存が生じるため、安定性の観点からは音声ファイルを事前にダウンロードしてローカルに保存することを推奨）。ピンインが3形式（声調なし・声調符号付き・数字声調）で提供されている点も実装上便利。Pythonで `from datasets import load_dataset; ds = load_dataset("willfliaw/hsk-dataset")` と1行で読み込める。

---

## 例文付きの語彙JSON：clem109/hsk-vocabulary

- **URL**: https://github.com/clem109/hsk-vocabulary
- **ライセンス**: MIT
- **形式**: JSON（`hsk-vocab-json/` ディレクトリにレベル別ファイル）
- **フィールド**: `id`, `hanzi`, `pinyin`, `translations`（英語訳の配列）, **`examples`**（例文配列：`zh` / `pinyin` / `en`）
- **単語数**: HSK 2.0（1〜6級）の全語彙
- **音声**: なし
- **日本語訳**: なし

**他のデータセットにはない例文データが含まれている点が最大の差別化ポイント**。例文は中国語・ピンイン・英語訳の3点セットで構成されており、単語カード的な学習だけでなく文脈での用法確認にも使える。HSK1の例：`{"zh": "我爱你", "pinyin": "wǒ ài nǐ", "en": "I love you"}`。コミュニティ主導で例文が追加されているため、カバレッジにはばらつきがある。

---

## 音声データ単体の補完リソース

音声が不足する単語を補う手段として、以下のリソースが有効。

**Shtooka Project**（http://shtooka.net/download.php）は audio-cmn の元データ元であり、FLAC形式のオリジナル音源を直接ダウンロードできる。「Base Audio Libre De Mots Chinois (HSK1)」はCC-BY 2.0 FR、「Collection Congcong」はCC-BY 3.0 US、「Collection Yue Tan」はCC-BY-SA 3.0 USでライセンスされている。

**Tone Perfect**（https://tone.lib.msu.edu/）はミシガン州立大学が公開する単音節音声データベースで、全410の中国語音節 × 4声調 × 6名のネイティブスピーカー＝**9,840ファイル**をプロフェッショナルなスタジオ録音で提供する。ライセンスはCC-BY-4.0。声調練習機能の実装に特に有効だが、単語レベルではなく音節レベルのデータである点に注意。

**MeloTTS**（https://github.com/myshell-ai/MeloTTS、MITライセンス）は、上記の録音データでカバーできない単語に対するフォールバックとして使えるオープンソース中国語TTSモデル。Pythonで `pip install melo-tts` してプログラム的にWAV/MP3を生成でき、CPU上でもリアルタイムに動作する。ビルド時にHSK1〜3級の全単語（約1,200〜3,000語）のMP3を事前生成しておく運用が現実的。

---

## HSK 3.0（新HSK）対応のCSVデータ

2021年に改訂されたHSK 3.0に対応したデータが必要な場合、**ivankra/hsk30**（https://github.com/ivankra/hsk30）が最も信頼性が高い。MITライセンスで、11,092語をCSV形式で提供。フィールドにはID（Ln-nnnn形式）、簡体字、繁体字、声調符号付きピンイン、品詞（英語コード）、レベル、バリアント（JSON）が含まれる。英語定義は直接含まれないが、CC-CEDICTエントリとのクロスリファレンスキーが付属している。`hsk30-expanded.csv` は全バリアントを個別行に展開済みで、プログラム処理に便利。文法リスト（`hsk30-grammar.csv`）も同梱されている。

**krmanik/HSK-3.0**（https://github.com/krmanik/HSK-3.0、180スター）は公式PDFのOCRに基づくデータで、注音符号（ボポモフォ）が含まれる唯一のデータセット。Ankiデッキ形式でも提供されている。

---

## 実装のためのアーキテクチャ推奨構成

データの組み合わせ方として、オープンソースの中国語学習アプリ **wenbun**（https://github.com/ray-pH/wenbun、Apache-2.0）が優れた参考実装になる。Svelte + Tauriで構築されたこのアプリは、`complete-hsk-vocabulary`（語彙）、`audio-cmn`（音声）、`hanzi-writer`（筆順アニメーション）、Lingua Libre（追加音声）、Open FSRS（間隔反復アルゴリズム）を統合しており、まさにユーザーが構築したいアプリの実動するブループリントである。

推奨するデータスタックは以下のとおり：

- **語彙データ**: `complete-hsk-vocabulary`（JSON / MIT）→ HSK1〜3級のファイルを抽出して使用
- **音声データ**: `audio-cmn`（MP3 / CC-BY-SA）→ 静的アセットとしてCDNから配信
- **音声の不足分**: MeloTTS（MIT）でビルド時に事前生成
- **例文データ**: `clem109/hsk-vocabulary`（JSON / MIT）
- **筆順アニメーション**: Hanzi Writer（https://hanziwriter.org/、MIT）→ 9,000字以上のSVGストロークデータ
- **日本語訳の補完**: JMdictや中日辞書データとの漢字マッチングで自動付与（オープンなHSKデータに日本語訳を含むものは現時点で皆無）

---

## 全データセット比較表

| データセット | 形式 | HSK版 | 単語数 | 音声 | ピンイン | 英語 | 例文 | ライセンス |
|---|---|---|---|---|---|---|---|---|
| complete-hsk-vocabulary | JSON | 2.0+3.0 | ~11,000 | ✗ | ✓ | ✓ | ✗ | MIT |
| audio-cmn | MP3 | 2.0 | 8,596 | **✓** | — | — | — | CC-BY-SA |
| willfliaw/hsk-dataset | CSV | 2.0 | ~5,000 | **✓**(TTS URL) | ✓(3形式) | ✓ | ✗ | CC-BY-4.0 |
| clem109/hsk-vocabulary | JSON | 2.0 | ~5,000 | ✗ | ✓ | ✓ | **✓** | MIT |
| ivankra/hsk30 | CSV | 3.0 | 11,092 | ✗ | ✓ | △(CEDICT参照) | ✗ | MIT |
| krmanik/HSK-3.0 | TXT/Anki | 3.0 | 全級 | ✗ | ✓+注音 | ✓ | ✗ | Custom |
| glxxyz/hskhsk.com | TSV | 2.0 | ~5,000 | ✗ | ✓(2形式) | ✓ | △(HSK1-3のみ) | 非商用 |
| Tone Perfect | MP3 | — | 9,840音節 | **✓** | — | — | — | CC-BY-4.0 |
| MeloTTS | 生成 | — | 無制限 | **✓**(生成) | — | — | — | MIT |

## 結論：日本語訳の壁をどう越えるか

CC-CEDICTを除く選択肢の中で、**`complete-hsk-vocabulary` + `audio-cmn` の組み合わせが、カバレッジ・ライセンスの明確さ・Webアプリへの組み込みやすさの3点でもっとも実用的**である。音声なし語彙データとしては前者が、音声単体としては後者が、それぞれの分野で最良のオープンリソースとなっている。

ただし、**日本語訳を含むオープンなHSKデータセットは現時点で存在しない**という点が最大の課題である。対処法としては、漢字の一致を利用してJMdict（和英辞書、CC-BY-SA）やCJK共通漢字のマッピングで自動的に日本語訳を付与する方法が現実的。日中で同形同義の語（例：「经济」→「経済」）は自動マッチが容易だが、同形異義語（例：「勉强」＝「無理に」≠「勉強」）には手動チェックが必要になる。wenbunプロジェクトのアーキテクチャを参考にしつつ、これらのデータソースを統合すれば、HSK1〜3級に対応した音声付き学習Webアプリを十分に構築できる。
