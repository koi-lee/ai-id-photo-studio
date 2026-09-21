# AI ID Photo Studio — AI証明写真ワークフロー

[简体中文](README.md) · [English](README.md#english) · [繁體中文](README.zh-Hant.md) · 日本語 · [한국어](README.ko.md)

AIによる服装・髪型・背景の変更案と、Pythonによるローカル画像処理を組み合わせるオープンソースのAgentスキルです。単独のオンライン証明写真サービスではありません。

## できること

- AI画像サービスを利用した服装・髪型・背景のプレビュー。
- カップル写真のコーディネート例：白シャツ、黒スーツ、グレースーツ、中国風の衣装、青と白のシャツ。
- ローカルでのトリミング、リサイズ、出力サイズの切り替え。
- 顔の形状を局所的に調整するツールと、画質・変更箇所を確認する手順。

![AIモデルによるカップル写真の例](examples/couple/couple-white-shirts-red-preview.png)

[5種類の作例と制限事項](examples/couple/README.md)（中国語）。作例はAI生成モデルであり、実在する夫婦の写真ではありません。カップル作例は内蔵画像生成ツールで制作したもので、このリポジトリのスクリプトによる生成性能の検証結果ではありません。

## 対応範囲と注意点

主に中国で使われる写真サイズのプリセットを収録しています。**日本のパスポート、マイナンバーカード、履歴書などの個別要件への適合は検証していません。** 日本語化は日本向け証明写真への対応を意味しません。

生成画像の受理や本人らしさは保証しません。正式な申請には提出先の最新要件に従ってください。合成カップル写真はスタイル確認用です。

## ローカルで試す

Python 3.10以上を用意し、リポジトリのルートで実行します。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python skill/scripts/process_id_photo.py examples/male/base-portrait.jpg --spec 1inch --outdir output/demo --no-watermark
```

Windowsでは有効化に `.venv\Scripts\activate` を使用します。この例は既存画像の後処理です。AIによる服装変更は行いません。

Agentで使う場合は `skill/` 全体を利用するAgentのスキルディレクトリにコピーします。[手順と実行例](docs/usage-examples.md)・[スキル本体](skill/SKILL.md)は中国語です。

## 費用・プライバシー

コードは[MITライセンス](LICENSE)です。画像生成サービスには別途料金がかかる場合があります。ローカル処理は画像を外部へ送りませんが、リモート生成を選ぶ場合は入力画像がそのサービスへ送信されます。本人や家族の写真・派生画像を公開リポジトリへ追加しないでください。

このページは概要と導入手順の翻訳です。全ドキュメントの翻訳や日本語UIの提供ではありません。
