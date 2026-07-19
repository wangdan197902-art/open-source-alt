---
title: "Slack"
vendor: "Salesforce"
category: "team-communication"
openSourceAlternative: "Element"
license: "AGPL-3.0"
aiGenerated: true
reviewStatus: "approved"
description: "Slackのオープンソース代替：Element"
---

# Slack → Element

## ソフトウェア情報
- 商用ソフトウェア：Slack
- オープンソース代替：Element
- ベンダー：Salesforce
- ライセンス：AGPL-3.0（Matrix プロトコル基盤）

## 機能比較
| 機能 | Slack | Element |
|------|-------|---------|
| チャンネル | ✅ | ✅ |
| ダイレクトメッセージ | ✅ | ✅ |
| スレッド | ✅ | ✅ |
| エンドツーエンド暗号化 | ⚠️ エンタープライズのみ | ✅ デフォルト |
| セルフホスト | ❌ | ✅ |
| 音声/ビデオ通話 | ✅ | ✅ |
| ボットと連携 | ✅ | ✅ |

## 利点
- 分散型プロトコル（Matrix）
- デフォルトのエンドツーエンド暗号化
- セルフホスト可能でデータ主権を完全保持
- サーバー間の連邦通信

## 欠点
- Slack ほど洗練された UX ではない
- 連携マーケットが小さい
- セルフホストの場合はサーバー運用が必要

## 移行難易度
**中** — チャンネル構造は直接マッピング可能ですが、Slack 固有のアプリやワークフローは Matrix ボットとブリッジに置き換える必要があります。ユーザーは連邦アイデンティティモデルに慣れる必要があります。
