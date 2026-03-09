# sequence.md
## 1日1冊短編小説サイト — シーケンス図

**Project:** DailyShortStorySite
**Version:** 1.2.0
**作成日:** 2026-03-09
**参照:** SPEC.md, UI.md, QandA.md

---

## 1. 日次パイプライン 通常フロー（automatic モード）

```mermaid
sequenceDiagram
    autonumber
    participant CRON as OpenClaw Cron
    participant MAIN as run_daily.py
    participant STATE as state.json
    participant PLOT as Plot Agent<br/>(generate_plot.py)
    participant TITLE as Title Selection Agent<br/>(select_title.py)
    participant STORY as Story Agent<br/>(generate_story.py)
    participant REVIEW as Review Agent<br/>(review_story.py)
    participant PUBLISH as Publish Agent<br/>(publish_story.py)
    participant STORIES as stories/<br/>（正本）
    participant SITE as site/_posts/<br/>（派生物）
    participant INDEX as data/stories_index.json
    participant GIT as GitHub Pages

    CRON->>MAIN: 日次起動（定時実行）
    MAIN->>STATE: state.json 読み込み
    STATE-->>MAIN: {stage, result, run_date, ...}

    alt 当日処理済み（result=published）
        MAIN-->>CRON: スキップして終了
    end

    MAIN->>STATE: stage=plot, result=in_progress 書き込み

    Note over MAIN,TITLE: === Plot Stage（タイトル選定含む）===

    MAIN->>PLOT: generate_plot 実行<br/>（used_themes, banned_terms 参照）
    PLOT-->>MAIN: artifacts/plot/<date>_plot.json 保存

    MAIN->>TITLE: select_title 実行<br/>（plot.json 参照）
    TITLE-->>MAIN: artifacts/plot/<date>_selected_title.json 保存

    MAIN->>STATE: stage=story, result=in_progress 書き込み

    Note over MAIN,STORIES: === Story Stage ===

    MAIN->>STORY: generate_story 実行<br/>（plot.json + selected_title.json + context bundle 参照）
    STORY-->>STORIES: stories/<year>/<slug>.md 保存<br/>（status: pending_review）
    STORY-->>MAIN: story draft 完了通知

    MAIN->>STATE: stage=review, result=in_progress 書き込み

    Note over MAIN,REVIEW: === Review Stage ===

    loop review 実行（初回 + 再生成後）
        MAIN->>REVIEW: review_story 実行<br/>（story JSON + banned_terms + stories_index直近30件 + 3-gram類似度 + AdSenseリスク）
        REVIEW-->>MAIN: review_score, ゲート判定, 合否判定

        alt 合格（review_score >= 80 かつ各下限・ゲート通過）
            MAIN->>MAIN: publish 判定へ進む
        else 不合格 かつ quality_retry_count < 3
            MAIN->>STATE: quality_retry_count++ 書き込み
            MAIN->>STORY: 本文再生成（同一入力セット）
            STORY-->>STORIES: stories/<year>/<slug>.md 上書き
        else 不合格 かつ quality_retry_count = 3
            MAIN->>STATE: stage=review, result=failed 書き込み
            MAIN->>MAIN: Windows通知（powershell.exe -NoProfile -File scripts/notify_failure.ps1）
            MAIN->>MAIN: logs/<date>/review.json にログ保存
            MAIN-->>CRON: 異常終了
        end
    end

    opt レビュー合格時のみ
        Note over MAIN,GIT: === Publish Stage ===

        MAIN->>STATE: stage=publish, result=in_progress 書き込み

        MAIN->>PUBLISH: validate_canonical_story<br/>（stories/ 正本確認）
        PUBLISH-->>MAIN: OK

        MAIN->>PUBLISH: sync_site_post<br/>（stories/ → site/_posts/ コピー）
        PUBLISH-->>SITE: site/_posts/YYYY-MM-DD-title.md 生成・更新

        MAIN->>PUBLISH: update_story_index<br/>（アトミック更新）
        PUBLISH-->>INDEX: stories_index.json 日付降順更新

        MAIN->>PUBLISH: git_commit_push
        PUBLISH-->>GIT: git commit && git push → GitHub Pages 公開

        MAIN->>STATE: stage=done, result=published 書き込み
        MAIN-->>CRON: 正常終了
    end
```

---

## 2. manual_review モード フロー

```mermaid
sequenceDiagram
    autonumber
    participant CRON as OpenClaw Cron
    participant MAIN as run_daily.py
    participant STATE as state.json
    participant PLOT as Plot Agent
    participant STORY as Story Agent
    participant REVIEW as Review Agent
    participant PENDING as pending/<br/>（承認待ちメタ）
    participant STORIES as stories/<br/>（正本）
    participant OPS as オペレーター
    participant PUBLISH as Publish Agent
    participant SITE as site/_posts/
    participant INDEX as data/stories_index.json
    participant GIT as GitHub Pages

    CRON->>MAIN: 日次起動
    MAIN->>STATE: publication_mode=manual_review 確認
    MAIN->>STATE: stage=plot, result=in_progress 書き込み

    MAIN->>PLOT: generate_plot + select_title 実行
    PLOT-->>MAIN: artifacts/plot/ に保存完了

    MAIN->>STATE: stage=story, result=in_progress 書き込み
    MAIN->>STORY: generate_story 実行
    STORY-->>STORIES: stories/<year>/<slug>.md 保存

    MAIN->>STATE: stage=review, result=in_progress 書き込み

    loop review 実行（初回 + 再生成後）
        MAIN->>REVIEW: review_story 実行
        REVIEW-->>MAIN: review_score, ゲート判定, 合否判定

        alt 合格（review_score >= 80 かつ各下限・ゲート通過）
            MAIN->>STATE: stage=pending_review, result=passed 書き込み
            MAIN->>PENDING: <slug>.pending.json 配置<br/>（slug, 正本パス, レビュー要約, 作成日時）
            MAIN-->>OPS: 承認待ち通知
        else 不合格 かつ quality_retry_count < 3
            MAIN->>STATE: quality_retry_count++ 書き込み
            MAIN->>STORY: 本文再生成（同一入力セット）
            STORY-->>STORIES: stories/<year>/<slug>.md 上書き
        else 不合格 かつ quality_retry_count = 3
            MAIN->>STATE: stage=review, result=failed 書き込み
            MAIN->>MAIN: Windows通知 + logs/<date>/review.json 保存
            MAIN-->>OPS: 失敗通知
        end
    end

    opt オペレーター承認後のみ
        OPS->>MAIN: 承認操作

        Note over MAIN,GIT: publish 共通パスへ進む
        MAIN->>STATE: stage=publish, result=in_progress 書き込み
        MAIN->>PUBLISH: validate_canonical_story
        MAIN->>PUBLISH: sync_site_post
        PUBLISH-->>SITE: site/_posts/YYYY-MM-DD-title.md 生成
        MAIN->>PUBLISH: update_story_index
        PUBLISH-->>INDEX: stories_index.json 更新
        MAIN->>PUBLISH: git_commit_push
        PUBLISH-->>GIT: GitHub Pages 公開
        MAIN->>STATE: stage=done, result=published 書き込み
    end
```

---

## 3. 差し戻し後フロー（manual_review + オペレーター差し戻し）

```mermaid
sequenceDiagram
    autonumber
    participant OPS as オペレーター
    participant MAIN as run_daily.py
    participant STATE as state.json
    participant STORIES as stories/<br/>（正本）
    participant REVIEW as Review Agent
    participant PUBLISH as Publish Agent
    participant SITE as site/_posts/
    participant INDEX as data/stories_index.json
    participant GIT as GitHub Pages

    Note over OPS,STATE: pending_review 状態から差し戻し

    OPS->>STORIES: stories/<year>/<slug>.md 修正（正本を直接編集）
    OPS->>MAIN: 差し戻し・再レビュー実行指示

    MAIN->>STATE: stage=review, result=in_progress 書き込み

    MAIN->>REVIEW: review_story 実行<br/>（初回と同一入力セット + rewrite_instruction 追加可）
    REVIEW-->>MAIN: review_score 返却

    alt 再レビュー合格
        Note over MAIN,GIT: publish 共通パスへ進む（差し戻し版も同一サブステップを実行）
        MAIN->>STATE: stage=publish, result=in_progress 書き込み
        MAIN->>PUBLISH: validate_canonical_story<br/>（stories/ 正本確認）
        PUBLISH-->>MAIN: OK
        MAIN->>PUBLISH: sync_site_post
        PUBLISH-->>SITE: site/_posts/YYYY-MM-DD-title.md 生成・更新
        MAIN->>PUBLISH: update_story_index
        PUBLISH-->>INDEX: stories_index.json アトミック更新
        MAIN->>PUBLISH: git_commit_push
        PUBLISH-->>GIT: GitHub Pages 公開
        MAIN->>STATE: stage=done, result=published 書き込み
        MAIN-->>OPS: 公開完了通知
    else 再レビュー不合格
        MAIN-->>OPS: 再度差し戻し通知
    end
```

---

## 4. 障害復旧フロー

```mermaid
sequenceDiagram
    autonumber
    participant CRON as OpenClaw Cron / 手動実行
    participant MAIN as run_daily.py
    participant STATE as state.json
    participant ART as artifacts/
    participant STORIES as stories/<br/>（正本）
    participant PLOT as Plot Agent
    participant TITLE as Title Selection Agent
    participant STORY as Story Agent
    participant REVIEW as Review Agent
    participant PUBLISH as Publish Agent
    participant SITE as site/_posts/
    participant INDEX as data/stories_index.json
    participant GIT as GitHub Pages

    CRON->>MAIN: 再実行
    MAIN->>STATE: state.json 読み込み
    STATE-->>MAIN: {stage, result, ...}

    alt stage=plot かつ plot.json あり、selected_title.json なし
        Note over MAIN,TITLE: Title Selection から再開
        MAIN->>TITLE: select_title 再実行
        TITLE-->>ART: artifacts/plot/<date>_selected_title.json 保存
        MAIN->>MAIN: 通常フロー（story）へ合流

    else stage=plot かつ plot.json なし
        Note over MAIN,PLOT: Plot 生成から再開
        MAIN->>PLOT: generate_plot 再実行
        PLOT-->>ART: artifacts/plot/<date>_plot.json 保存
        MAIN->>TITLE: select_title 実行
        TITLE-->>ART: artifacts/plot/<date>_selected_title.json 保存
        MAIN->>MAIN: 通常フロー（story）へ合流

    else stage=story
        Note over MAIN,STORY: 正本ドラフト有無で判断
        MAIN->>STORIES: stories/<year>/<slug>.md 存在確認
        alt 正本ドラフトあり
            MAIN->>MAIN: 通常フロー（review）へ合流
        else 正本ドラフトなし
            MAIN->>STORY: generate_story 再実行
            MAIN->>MAIN: 通常フロー（review）へ合流
        end

    else stage=review
        Note over MAIN,REVIEW: 同一入力で再レビュー
        MAIN->>REVIEW: review_story 再実行（初回と同一入力セット）
        REVIEW-->>MAIN: review_score 返却
        MAIN->>MAIN: 通常フロー（publish判定）へ合流

    else stage=publish
        Note over MAIN,GIT: 公開サブステップを冪等再実行
        MAIN->>STATE: stage=publish, result=in_progress 書き込み（既存なら上書き）
        MAIN->>PUBLISH: validate_canonical_story
        PUBLISH-->>MAIN: OK
        MAIN->>PUBLISH: sync_site_post（冪等）
        PUBLISH-->>SITE: site/_posts/YYYY-MM-DD-title.md 上書き
        MAIN->>PUBLISH: update_story_index（冪等）
        PUBLISH-->>INDEX: stories_index.json 再計算更新
        MAIN->>PUBLISH: git_commit_push（冪等）
        PUBLISH-->>GIT: GitHub Pages 公開（差分なければ no-op）
        MAIN->>STATE: stage=done, result=published 書き込み

    else stage=done または result=published
        MAIN-->>CRON: 当日スキップして終了
    end
```

---

## 5. Codex CLI 実行失敗リトライフロー

```mermaid
sequenceDiagram
    autonumber
    participant MAIN as run_daily.py
    participant CODEX as Codex CLI<br/>（GPT-5.4）
    participant STATE as state.json
    participant LOG as logs/<date>/
    participant NOTIFY as notify_failure.ps1<br/>（Windows通知）

    Note over MAIN,CODEX: 品質リジェクト以外の実行失敗（タイムアウト、ネットワーク障害、クラッシュ等）

    MAIN->>CODEX: CLI 実行（1回目）
    CODEX-->>MAIN: 失敗（非ゼロ終了 / タイムアウト / 応答破損）

    MAIN->>MAIN: 60秒 待機

    MAIN->>CODEX: CLI 再実行（2回目）
    CODEX-->>MAIN: 失敗

    MAIN->>MAIN: 300秒 待機

    MAIN->>CODEX: CLI 再実行（3回目）

    alt 成功
        CODEX-->>MAIN: 正常応答
        MAIN->>MAIN: 通常フロー継続
    else 3回目も失敗
        CODEX-->>MAIN: 失敗
        MAIN->>STATE: stage 維持, result=failed 書き込み
        MAIN->>LOG: 標準出力・標準エラー・例外情報 保存<br/>（logs/<date>/run.log）
        MAIN->>NOTIFY: powershell.exe -NoProfile -File scripts/notify_failure.ps1 呼び出し
        NOTIFY-->>MAIN: Windows通知送信（失敗してもログは保存済み）
        MAIN-->>MAIN: 異常終了

        Note over MAIN,STATE: 次回 cron 実行時は同一 stage から再開<br/>quality_retry_count は増やさない
    end
```

---

## 6. 類似度検査フロー（3-gram Jaccard）

```mermaid
sequenceDiagram
    autonumber
    participant REVIEW as Review Agent
    participant SIM as similarity_check.py
    participant INDEX as data/stories_index.json
    participant MAIN as run_daily.py

    REVIEW->>SIM: 類似度検査実行<br/>（新作の title + summary を渡す）
    SIM->>INDEX: 直近90日の {title + summary} 取得
    INDEX-->>SIM: 過去作品リスト返却

    loop 過去作品ごとに比較
        SIM->>SIM: 新作と過去作の文字3-gramセット生成
        SIM->>SIM: Jaccard類似度 = |A∩B| / |A∪B| 計算
    end

    SIM-->>REVIEW: 最大類似度スコア（0〜1）と対象 slug 返却

    alt 最大類似度 >= 0.40
        REVIEW->>MAIN: 差し戻し候補（類似度超過）フラグ付きで返却
        MAIN->>MAIN: review_score にペナルティ or 不合格処理
    else 最大類似度 < 0.40
        REVIEW->>MAIN: 類似度OK として継続
    end
```

---

## 7. 状態遷移サマリ

```mermaid
sequenceDiagram
    autonumber
    participant STATE as state.json
    Note over STATE: stage 遷移とトリガー

    STATE->>STATE: start（当日未着手）
    STATE->>STATE: → plot（Plot Agent 開始）
    STATE->>STATE: → story（Plot 完了後）
    STATE->>STATE: → review（Story 生成完了後）
    STATE->>STATE: → pending_review（manual_review モード、合格時）
    STATE->>STATE: → publish（合格後 automatic / 承認後 manual）
    STATE->>STATE: → done（publish 完了後）

    Note over STATE: result 遷移
    STATE->>STATE: idle
    STATE->>STATE: → in_progress（各 stage 開始時）
    STATE->>STATE: → passed（review 合格）
    STATE->>STATE: → failed（品質3回失敗 or 実行失敗）
    STATE->>STATE: → published（publish 完了）
```

---

*本ドキュメントは SPEC.md §8（状態管理）、§9（Plot Stage）、§14（品質判定）、§15（publish 責務）、§16〜19（フロー・障害復旧）に基づいて設計。*
