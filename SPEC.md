# SPEC.md
## 1日1冊短編小説サイト 仕様書（改訂版）
**Project Name:** DailyShortStorySite  
**Version:** 1.2.0  
**Date:** 2026-03-09  
**Primary Runtime:** Windows 11 + WSL2  
**Scheduler:** OpenClaw Cron  
**Main Generation Engine:** Codex CLI 定額利用（GPT-5.4）  
**Publishing Target:** GitHub Pages (`garyohosu.github.io/writer`)  
**Monetization Requirement:** Google AdSense 必須

---

## 1. 目的

本システムは、Codex CLI の定額利用環境を用いて、毎日1本の日本語短編小説を生成・審査・公開する静的サイトを構築することを目的とする。既定運用は全自動公開とし、OpenClaw cron の日次実行だけで公開完了まで到達することを前提とする。

本改訂版では、以下を明確化する。

- `automatic` を既定とした状態遷移
- 作品正本の保存先
- `baseurl` を含む GitHub Pages のURL設計
- 日本語向け類似度検査
- publish 段階の責務分解と復旧方式
- Title Selection の復旧単位
- 文字数単位の統一


googleアドセンスを各ページに入れておくこと
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6743751614716161"
     crossorigin="anonymous"></script>

各ページはCDNを使ったモダン技術ブログ的外観のサイトとすること


---

## 2. スコープ

### 2.1 対象範囲
- 毎日1作品の短編小説生成
- プロット生成
- タイトル選定
- 本文生成
- 自動レビュー
- 手動レビュー
- Markdown 正本保存
- GitHub Pages 用派生物生成
- stories index 更新
- Git push による公開
- AdSense 対応テンプレート運用
- OpenClaw cron による日次実行
- 状態管理と障害復旧

### 2.2 対象外
- 会員登録
- コメント機能
- 決済機能
- 動的サーバーAPI
- 高度な推薦機能
- 完全自律の無制限改善ループ

---

## 3. 前提条件

### 3.1 実行環境
- Windows 11
- WSL2 (Ubuntu 想定)
- Python 3.11+
- Git
- Codex CLI
- OpenClaw
- GitHub Pages
- Jekyll (Chirpy 想定)
- Google AdSense

### 3.2 AI利用前提
- 本文生成・レビューは Codex CLI + GPT-5.4 を主に利用する
- API課金ベースではなく CLI 実行ベースで設計する
- タイトル選定は独立 Agent として扱うが、状態管理上は `plot` に内包する
- 将来のローカル補助検査は拡張扱いとする

### 3.3 公開前提
- GitHub Pages はサブパス運用とする
- `url: "https://garyohosu.github.io"`
- `baseurl: "/writer"`
- `permalink: /posts/:slug/`

---

## 4. サイト方針

### 4.1 コンセプト
- 毎日1話完結の短編小説を公開する
- 読了時間は 3〜8分程度
- 作品同士にゆるい統一感を持たせる
- 読者がその日だけ来ても読める構成にする

### 4.2 推奨テーマ
- 日常の中の小さな不思議
- 猫が関わる短編
- 仕事帰りに読める余韻のある話
- 軽いSF
- 微ファンタジー

### 4.3 文体制約
- 過剰説明を避ける
- 特定作家模倣を禁止する
- 既存作品の焼き直しを避ける
- 冒頭3行で引き込む
- 読後感を設計する

---

## 5. Canonical Source と派生物の定義

この仕様では、保存先の責務を以下に固定する。

### 5.1 正本
- `stories/` を作品 Markdown の **唯一の正本** とする

### 5.2 承認待ち
- `pending/` は `manual_review` 用の承認待ち参照置き場とする
- `pending/` は正本ではない
- 必要に応じて `stories/` 正本へのリンクまたはコピーを置いてよい

### 5.3 公開用派生物
- `site/_posts/` は Jekyll 公開用の **派生物** とする
- 編集・再レビュー・再公開判断は `site/_posts/` ではなく `stories/` を参照する

### 5.4 JSON管理物
- `data/stories_index.json` は公開済み作品一覧
- `data/state.json` はパイプライン状態
- `data/used_themes.json` は直近テーマ履歴
- `data/banned_terms.json` は禁止語・禁止表現辞書

---

## 6. ディレクトリ構成

```text
project-root/
  SPEC.md
  README.md
  prompts/
    plot_prompt.md
    title_prompt.md
    story_prompt.md
    review_prompt.md
  data/
    state.json
    stories_index.json
    used_themes.json
    banned_terms.json
  artifacts/
    plot/
    review/
    context/
  stories/
    2026/
      2026-03-09-midnight-cat.md
  pending/
    2026-03-09-midnight-cat.md
  logs/
    2026-03-09/
      run.log
      review.json
      publish.log
  scripts/
    run_daily.py
    generate_plot.py
    select_title.py
    generate_story.py
    review_story.py
    publish_story.py
    rebuild_indexes.py
    similarity_check.py
  site/
    _config.yml
    _posts/
    _includes/
    ads.txt
    privacy-policy.md
    contact.md
```

---

## 7. 作品メタデータ仕様

### 7.1 文字数単位
本システムでは **単語数ではなく文字数** を正式単位とする。  
`word_count` は使用せず、すべて `character_count` に統一する。

### 7.2 作品要件
- 1日1作品
- 2,000〜5,000文字
- タイトル、要約、タグ、公開日、文字数を持つ
- 一意の slug を持つ
- `ai_generated: true` を持つ

### 7.3 Markdown 形式

```md
---
title: "夜勤明けの猫はエレベーターを待っていた"
date: "2026-03-09"
slug: "2026-03-09-midnight-cat"
tags: ["猫", "日常", "不思議"]
genre: "短編"
theme: "疲れた心に小さな異界が触れる"
character_count: 3120
reading_time_min: 6
status: "pending_review"
summary: "夜勤明けの技術者が、会社の片隅で奇妙な猫に出会う短編。"
ai_generated: true
review_score: 86
canonical_source: "stories"
---
本文...
```

---

## 8. 状態管理仕様

### 8.1 state.json 例

```json
{
  "run_date": "2026-03-09",
  "publication_mode": "automatic",
  "stage": "plot",
  "result": "in_progress",
  "last_published_slug": "2026-03-08-rain-window",
  "current_slug": "2026-03-09-midnight-cat",
  "retry_count": 0,
  "artifacts": {
    "plot_bundle": true,
    "story_draft": false,
    "review_report": false,
    "pending_copy": false,
    "site_post_synced": false,
    "index_updated": false,
    "git_pushed": false
  }
}
```

### 8.2 publication_mode
- `automatic`
- `manual_review`

既定値は `automatic` とする。

### 8.3 stage
- `start`
- `plot`
- `story`
- `review`
- `pending_review`
- `publish`
- `done`

### 8.4 result
- `idle`
- `in_progress`
- `passed`
- `failed`
- `published`

### 8.5 stage の意味
- `plot`: プロット生成とタイトル選定を含む
- `story`: 本文生成
- `review`: 自動レビュー
- `pending_review`: 補助的な人手確認待ち
- `publish`: 公開サブステップ実行中
- `done`: 当日処理完了

---

## 9. Plot Stage と Title Selection の扱い

### 9.1 基本方針
Title Selection Agent は **独立 Agent** として実装するが、状態管理上は `plot` stage に内包する。

### 9.2 plot stage の内部サブステップ
1. `generate_plot`
2. `select_title`
3. `persist_plot_bundle`

### 9.3 plot 完了条件
以下が揃った時のみ `plot` 完了とする。

- `artifacts/plot/<date>_plot.json`
- `artifacts/plot/<date>_selected_title.json`

### 9.4 plot 復旧
- `plot.json` が存在し、`selected_title.json` が存在しない場合は **Title Selection から再開**
- 両方なければ Plot から再開
- state の `stage` は `plot` のまま維持する

---

## 10. stories_index.json 仕様

### 10.1 並び順
`stories_index.json` は **日付降順** で保持する。

### 10.2 例

```json
[
  {
    "date": "2026-03-09",
    "slug": "2026-03-09-midnight-cat",
    "title": "夜勤明けの猫はエレベーターを待っていた",
    "summary": "夜勤明けの技術者が、会社の片隅で奇妙な猫に出会う短編。",
    "tags": ["猫", "日常", "不思議"],
    "character_count": 3120,
    "reading_time_min": 6,
    "review_score": 86
  }
]
```

### 10.3 更新方式
- 一時ファイルを作成してから差し替えるアトミック更新とする
- publish 復旧時は毎回再計算または冪等更新してよい

---

## 11. AIエージェント構成

### 11.1 Plot Agent
- 今日のテーマを生成
- 過去作と被りにくいプロットを作る
- 主要登場人物、舞台、転換点、結末を設計する

### 11.2 Title Selection Agent
- タイトル候補を比較採点する
- プロットに最も適合したタイトルを1件選ぶ
- タイトル選定結果を JSON で保存する

### 11.3 Story Agent
- プロットとタイトルから本文を書く
- 指定文字数に収める
- 文体制約を守る

### 11.4 Review Agent
- 読みやすさ
- 一貫性
- 類似度
- 禁止表現
- AdSense リスク
- 冒頭の引き
- 結末の余韻
を点検する

### 11.5 Publish Agent
- `stories/` 正本を検証
- `site/_posts/` へ同期
- `stories_index.json` 更新
- Git commit / push
- `published` へ遷移

---

## 12. 類似度検査仕様（日本語対応）

### 12.1 方針
ローカル類似度検査は、日本語で `split()` ベース Jaccard を使わない。

### 12.2 採用方式
- 比較単位は **文字 3-gram**
- 類似度指標は 3-gram Jaccard
- 比較対象は直近90日の `title + summary`
- しきい値超過時は Review Agent が差し戻し候補とする

### 12.3 将来拡張
- 形態素解析ベースへ差し替え可能
- embedding 類似度導入は将来拡張扱い

---

## 13. 自動レビュー入力仕様

### 13.1 初回レビュー入力
- `story JSON`
- `banned_terms.json`
- `stories_index.json` の直近30作品
- 3-gram 類似度検査結果
- publication mode
- AdSense リスク観点

### 13.2 再生成後レビュー入力
初回と **同一セット** を渡す。  
レビュー入力を弱めてはならない。

### 13.3 オペレーター差し戻し後レビュー入力
初回と **同一セット** を渡す。  
必要に応じて `rewrite_instruction` を追加してよい。

---

## 14. 品質判定基準

### 14.1 評価軸
- 独自性
- 読みやすさ
- 一貫性
- 冒頭の引き
- 結末の余韻
- 禁止事項抵触
- AdSense適合性

### 14.2 合格条件
- 独自性: 80点以上
- 読みやすさ: 75点以上
- 一貫性: 85点以上
- 総合: 80点以上
- 禁止事項: 問題なし
- AdSense リスク: 許容範囲

### 14.3 再生成
- 最大3回まで再生成する
- 3回失敗時は `stage=review, result=failed`
- Windows 通知 + ログ保存を行う

---

## 15. publish 段階の責務分解

### 15.1 publish は単一 stage + サブステップで扱う
publish は 1段処理ではなく、以下のサブステップを含む。

1. `validate_canonical_story`
2. `sync_site_post`
3. `update_story_index`
4. `git_commit_push`
5. `mark_published`

### 15.2 publish 開始時 state
publish 開始前に必ず以下を保存する。

```json
{
  "stage": "publish",
  "result": "in_progress"
}
```

### 15.3 publish 完了条件
- `stories/` 正本あり
- `site/_posts/` 同期済み
- `stories_index.json` 更新済み
- Git push 済み
- `state.result = published`

### 15.4 publish 復旧方針
**公開サブステップは常に冪等再実行する。**  
`git push` のみ再試行という特別扱いはしない。

### 15.5 publish 復旧時の再実行対象
- `sync_site_post`
- `update_story_index`
- `git_commit_push`
- `mark_published`

---

## 16. 通常フロー

### 16.1 automatic
1. OpenClaw cron が `run_daily.py` を起動
2. `state.json` を読み込む
3. 当日未着手なら `stage=start`
4. `plot` 実行
5. `story` 実行
6. `review` 実行
7. 合格なら `publish` 開始時に `stage=publish, result=in_progress`
8. `sync_site_post`
9. `update_story_index`
10. `git_commit_push`
11. `mark_published`
12. `stage=done, result=published`

### 16.2 manual_review（補助モード）
1. `plot`
2. `story`
3. `review`
4. 合格時 `stage=pending_review, result=passed`
5. `stories/` 正本保存
6. `pending/` に承認待ち配置
7. オペレーターが確認
8. 承認時に `publish` 共通処理へ進む
9. 公開後 `stage=done, result=published`

---

## 17. automatic 既定運用と manual_review 補助モード

### 17.1 automatic 既定運用
本システムの既定運用は `automatic` とする。  
自動レビュー合格後は、承認待ちを挟まず即座に publish 共通処理へ進む。

### 17.2 automatic 再実行時の扱い
- `failed` の場合: 失敗 stage から再開
- `publish` の場合: 公開サブステップを冪等再実行
- `published` の場合: 当日処理をスキップ
- `pending_review` は補助モード時のみ利用する

### 17.3 manual_review 補助モード
必要時のみ `manual_review` を選択できる。  
オペレーター差し戻し時は、`stories/` 正本を更新し、再レビューを実行する。承認後は **必ず共通 publish パス** を通る。

---

## 18. 差し戻し後フロー

### 18.1 共通原則
差し戻し後に承認された作品も、通常の manual publish と同じ publish サブステップを実行する。

### 18.2 必須サブステップ
- `stories/` 正本確認
- `site/_posts/` 同期
- `stories_index.json` 更新
- `git_commit_push`
- `state.result = published`

### 18.3 禁止事項
差し戻し版のみ `git push` だけで済ませてはならない。

---

## 19. 障害復旧仕様

### 19.1 stage ごとの再開
- `plot`: 保存済み artifact に応じて `generate_plot` または `select_title` から再開
- `story`: 正本ドラフトの有無で再生成判断
- `review`: 初回と同じ入力で再レビュー
- `pending_review`: 承認待ち維持
- `publish`: 公開サブステップを冪等再実行

### 19.2 既存公開物の保護
publish 完了前に失敗した場合、既存サイトを壊してはならない。

### 19.3 ログ
- `logs/<date>/run.log`
- `logs/<date>/review.json`
- `logs/<date>/publish.log`

---

## 20. GitHub Pages / Jekyll URL 仕様

### 20.1 `_config.yml`
```yml
url: "https://garyohosu.github.io"
baseurl: "/writer"
permalink: /posts/:slug/
```

### 20.2 URL生成
- 内部リンクは `site.baseurl` 前提で生成する
- ルート相対 `/posts/...` を直書きしてはならない

### 20.3 canonical / OGP
以下で統一する。

```text
{{ site.url }}{{ site.baseurl }}{{ page.url }}
```

---

## 21. AdSense 要件

### 21.1 必須
- AdSense コードをテンプレートへ埋め込む
- `ads.txt` をルートへ配置する
- `privacy-policy.md` を設置する
- `contact.md` を設置する
- AI生成作品である旨を明記する

### 21.2 広告枠
MVP の固定枠は以下の **3枠** に統一する。

1. 記事上部
2. 記事下部
3. 一覧下部

### 21.3 非採用
一覧上部広告は MVP では採用しない。

---

## 22. banned_terms / used_themes 運用

### 22.1 banned_terms
- 初期リストは手動作成する
- 差別語、露骨な暴力・性的語、実在作家名、危険表現を含む
- 運用中に追記して育てる

### 22.2 used_themes
- 直近90日を保持対象とする
- 同一テーマの短期再出現を抑制する

---

## 23. Python / 実行環境

### 23.1 Python 環境
- WSL2 上の `venv` を正式運用とする

### 23.2 方針
- Git 操作は WSL2 内で完結
- 改行は LF
- 秘密情報は `.env`
- OpenClaw から WSL コマンドを叩く

### 23.3 OpenClaw 実行例
```bash
wsl bash -lc 'cd /path/to/project && source .venv/bin/activate && python3 scripts/run_daily.py >> logs/cron.log 2>&1'
```

---

## 24. 受け入れ条件

以下を満たした場合に受け入れとする。

1. `automatic` 既定時にレビュー合格後そのまま publish へ進める
2. `manual_review` 選択時のみ `pending_review` で停止できる
3. `stories/` が正本として運用される
4. `site/_posts/` は派生物として同期される
5. `baseurl=/writer` 前提でリンク・canonical が生成される
6. 類似度検査が 3-gram Jaccard で実装される
7. `character_count` に統一される
8. publish 開始時に `stage=publish, result=in_progress` が保存される
9. publish 復旧時に公開サブステップを冪等再実行できる
10. Title Selection が `plot` stage 内で復旧可能である
11. 再レビュー入力が初回と同一である
12. AdSense 3枠が仕様とUIで一致する

---

## 25. 実装優先順位

### Phase 1
- 単発生成
- `stories/` 正本保存
- GitHub Pages 反映

### Phase 2
- 自動レビュー
- `pending_review`
- publish 復旧
- 類似度検査

### Phase 3
- AdSense最適化
- SEO整備
- UI調整

### Phase 4
- 英訳版
- 画像生成
- 音声化

---

## 26. 補足方針

今回の改訂では、Codex CLI を単に本文生成器として使うのではなく、状態管理・文脈固定・再開可能性を持つ小説生成基盤として扱う。  
そのため、タイトル選定、公開責務、承認待ち、類似度検査、日本語向け指標を明示的に仕様化する。

以上を改訂版仕様とする。
