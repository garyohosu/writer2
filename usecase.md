# usecase.md
## 1日1冊短編小説サイト — ユースケース図

**Project:** DailyShortStorySite
**Version:** 1.2.0
**作成日:** 2026-03-09
**参照:** SPEC.md, UI.md, QandA.md

---

## 1. アクター定義

| アクター | 区分 | 説明 |
|---|---|---|
| OpenClaw Cron | 主アクター（システム） | 毎日定時に日次パイプラインを起動するスケジューラ |
| オペレーター | 主アクター（人間） | manual_review モード時に作品を承認・差し戻しする管理者 |
| 読者 | 主アクター（人間） | GitHub Pages 上の公開サイトを閲覧する利用者 |
| Codex CLI | 副アクター（外部システム） | プロット・本文・レビューを生成する AI エンジン |
| GitHub Pages | 副アクター（外部システム） | 静的サイトをホスティングする公開基盤 |
| Google AdSense | 副アクター（外部システム） | 広告配信サービス |

---

## 2. ユースケース図 全体

```mermaid
flowchart TB
    %% ===== アクター =====
    CRON(["🕐 OpenClaw Cron\n（スケジューラ）"])
    OPS(["👤 オペレーター"])
    READER(["👥 読者"])
    CODEX(["🤖 Codex CLI\n（GPT-5.4）"])
    GITHUB(["☁️ GitHub Pages"])
    ADSENSE(["💰 Google AdSense"])

    %% ===== システム境界 =====
    subgraph SYS["DailyShortStorySite システム"]
        direction TB

        subgraph PIPELINE["日次生成パイプライン"]
            PIPE01(["PIPE-01\n日次パイプライン起動"])
            PIPE02(["PIPE-02\nプロット生成"])
            PIPE03(["PIPE-03\nタイトル選定"])
            PIPE04(["PIPE-04\n本文生成"])
            PIPE05(["PIPE-05\n自動レビュー実行"])
            PIPE06(["PIPE-06\n類似度検査"])
            PIPE07(["PIPE-07\n禁止語検査"])
            PIPE08(["PIPE-08\nAdSenseリスク検査"])
            PIPE09(["PIPE-09\n品質再生成"])
        end

        subgraph PUBFLOW["公開フロー"]
            PUB01(["PUB-01\n自動公開開始"])
            PUB02(["PUB-02\n承認待ち登録"])
            PUB03(["PUB-03\n作品承認"])
            PUB04(["PUB-04\n作品差し戻し"])
            PUB05(["PUB-05\n再レビュー実行"])
            PUB06(["PUB-06\npublish サブステップ実行"])
        end

        subgraph RECOVERY["障害復旧"]
            REC01(["REC-01\nパイプライン再開"])
            REC07(["REC-07\n実行失敗リトライ"])
            REC08(["REC-08\nWindows通知送信"])
        end

        subgraph SITE["サイト管理"]
            PUB07(["PUB-07\n正本検証（stories/）"])
            PUB08(["PUB-08\n派生物同期（site/_posts/）"])
            PUB09(["PUB-09\nstories_index.json 更新"])
            PUB10(["PUB-10\nGit commit / push"])
            PUB11(["PUB-11\npublished マーク"])
        end

        subgraph READER_UC["サイト閲覧"]
            VIEW01(["VIEW-01\nトップページ閲覧"])
            VIEW02(["VIEW-02\n作品一覧閲覧"])
            VIEW03(["VIEW-03\n作品詳細閲覧"])
            VIEW04(["VIEW-04\nタグ別一覧閲覧"])
            VIEW05(["VIEW-05\n前後作品ナビゲーション"])
            VIEW06(["VIEW-06\nこのサイトについて閲覧"])
            VIEW07(["VIEW-07\nプライバシーポリシー閲覧"])
            VIEW08(["VIEW-08\nコンタクトページ閲覧"])
            VIEW09(["VIEW-09\n広告閲覧"])
        end
    end

    %% ===== 関係線 =====
    CRON -->|起動| PIPE01
    PIPE01 -->|含む| PIPE02
    PIPE02 -->|含む| PIPE03
    PIPE03 -->|含む| PIPE04
    PIPE04 -->|含む| PIPE05
    PIPE05 -->|含む| PIPE06
    PIPE05 -->|含む| PIPE07
    PIPE05 -->|含む| PIPE08
    PIPE05 -->|不合格| PIPE09
    PIPE09 -->|再試行| PIPE04

    PIPE02 -.->|uses| CODEX
    PIPE03 -.->|uses| CODEX
    PIPE04 -.->|uses| CODEX
    PIPE05 -.->|uses| CODEX

    PIPE05 -->|合格 / automatic| PUB01
    PIPE05 -->|合格 / manual_review| PUB02
    PUB02 -->|通知| OPS
    OPS -->|承認| PUB03
    OPS -->|差し戻し| PUB04
    PUB03 -->|含む| PUB06
    PUB04 -->|含む| PUB05
    PUB05 -->|合格後| PUB06
    PUB01 -->|含む| PUB06

    PUB06 -->|含む| PUB07
    PUB06 -->|含む| PUB08
    PUB06 -->|含む| PUB09
    PUB06 -->|含む| PUB10
    PUB06 -->|含む| PUB11
    PUB10 -.->|push| GITHUB

    CRON -->|再実行| REC01
    OPS -->|手動再実行| REC01
    REC01 -->|含む| REC07
    REC07 -->|失敗時| REC08

    READER -->|アクセス| VIEW01
    READER -->|アクセス| VIEW02
    READER -->|アクセス| VIEW03
    READER -->|アクセス| VIEW04
    READER -->|アクセス| VIEW06
    READER -->|アクセス| VIEW07
    READER -->|アクセス| VIEW08
    VIEW03 -->|含む| VIEW05
    VIEW01 -.->|提供| GITHUB
    VIEW02 -.->|提供| GITHUB
    VIEW03 -.->|提供| GITHUB
    VIEW04 -.->|提供| GITHUB
    VIEW06 -.->|提供| GITHUB
    VIEW07 -.->|提供| GITHUB
    VIEW08 -.->|提供| GITHUB

    VIEW09 -.->|配信| ADSENSE
    READER -->|閲覧| VIEW09
```

---

## 3. 日次パイプライン ユースケース詳細

```mermaid
flowchart LR
    CRON(["🕐 OpenClaw Cron"])
    CODEX(["🤖 Codex CLI"])

    subgraph PIPE["日次パイプライン（run_daily.py）"]
        direction TB
        PIPE01(["PIPE-01\n日次パイプライン起動"])
        PIPE02(["PIPE-02\nプロット生成"])
        PIPE03(["PIPE-03\nタイトル選定"])
        PIPE04(["PIPE-04\n本文生成"])
        PIPE05(["PIPE-05\n自動レビュー実行"])
        PIPE06(["PIPE-06\n類似度検査\n（3-gram Jaccard）"])
        PIPE07(["PIPE-07\n禁止語検査\n（banned_terms）"])
        PIPE08(["PIPE-08\nAdSenseリスク検査"])
        PIPE09(["PIPE-09\n品質再生成\n（最大3回）"])

        PIPE01 --> PIPE02
        PIPE02 --> PIPE03
        PIPE03 --> PIPE04
        PIPE04 --> PIPE05
        PIPE05 -->|含む| PIPE06
        PIPE05 -->|含む| PIPE07
        PIPE05 -->|含む| PIPE08
        PIPE05 -->|不合格| PIPE09
        PIPE09 -->|再試行| PIPE04
    end

    CRON -->|起動| PIPE01
    PIPE02 -.->|生成依頼| CODEX
    PIPE03 -.->|選定依頼| CODEX
    PIPE04 -.->|生成依頼| CODEX
    PIPE05 -.->|レビュー依頼| CODEX
```

---

## 4. 公開フロー ユースケース詳細

```mermaid
flowchart LR
    OPS(["👤 オペレーター"])
    GITHUB(["☁️ GitHub Pages"])

    subgraph PUB["公開フロー"]
        direction TB

        subgraph AUTO["automatic モード"]
            PUB01(["PUB-01\n自動公開開始"])
            PUB06A(["PUB-06\npublish サブステップ実行"])
            PUB01 --> PUB06A
        end

        subgraph MANUAL["manual_review モード"]
            PUB02(["PUB-02\n承認待ち登録"])
            PUB03(["PUB-03\n作品承認"])
            PUB04(["PUB-04\n作品差し戻し"])
            PUB05(["PUB-05\n再レビュー実行"])
            PUB06B(["PUB-06\npublish サブステップ実行"])

            PUB02 -->|承認| PUB03
            PUB02 -->|差し戻し| PUB04
            PUB03 --> PUB06B
            PUB04 --> PUB05
            PUB05 -->|合格| PUB06B
        end

        subgraph SUB["publish サブステップ（共通）"]
            PUB07(["PUB-07\n正本検証\n（stories/）"])
            PUB08(["PUB-08\n派生物同期\n（site/_posts/）"])
            PUB09(["PUB-09\nstories_index.json 更新"])
            PUB10(["PUB-10\nGit commit / push"])
            PUB11(["PUB-11\npublished マーク"])

            PUB07 --> PUB08 --> PUB09 --> PUB10 --> PUB11
        end

        PUB06A --> PUB07
        PUB06B --> PUB07
    end

    OPS -->|承認操作| PUB03
    OPS -->|差し戻し操作| PUB04
    PUB10 -.->|push| GITHUB
```

---

## 5. 障害復旧 ユースケース詳細

```mermaid
flowchart LR
    CRON(["🕐 OpenClaw Cron"])
    OPS(["👤 オペレーター"])
    WIN(["🪟 Windows\n通知システム"])

    subgraph REC["障害復旧"]
        direction TB
        REC01(["REC-01\nパイプライン再開"])
        REC02(["REC-02\nplot から再開"])
        REC03(["REC-03\ntitle selection から再開"])
        REC04(["REC-04\nstory から再開"])
        REC05(["REC-05\nreview から再開"])
        REC06(["REC-06\npublish サブステップ冪等再実行"])
        REC07(["REC-07\nCLI 実行失敗リトライ\n（60秒 / 300秒）"])
        REC08(["REC-08\n失敗通知送信"])

        REC01 -->|stage=plot, 両方なし| REC02
        REC01 -->|stage=plot, plot.jsonあり| REC03
        REC01 -->|stage=story| REC04
        REC01 -->|stage=review| REC05
        REC01 -->|stage=publish| REC06

        REC07 -->|3回失敗| REC08
    end

    CRON -->|再実行| REC01
    OPS -->|手動再実行| REC01
    REC08 -.->|通知| WIN
    REC08 -.->|通知確認| OPS
```

---

## 6. サイト閲覧 ユースケース詳細

```mermaid
flowchart LR
    READER(["👥 読者"])
    ADSENSE(["💰 Google AdSense"])
    GITHUB(["☁️ GitHub Pages"])

    subgraph VIEW["サイト閲覧（GitHub Pages）"]
        direction TB
        VIEW01(["VIEW-01\nトップページ閲覧\n（最新作 + 直近5件）"])
        VIEW02(["VIEW-02\n作品一覧閲覧\n（日付降順 / タグフィルタ）"])
        VIEW03(["VIEW-03\n作品詳細閲覧\n（本文 + メタ情報）"])
        VIEW04(["VIEW-04\nタグ別一覧閲覧"])
        VIEW05(["VIEW-05\n前後作品ナビゲーション"])
        VIEW06(["VIEW-06\nこのサイトについて閲覧"])
        VIEW07(["VIEW-07\nプライバシーポリシー閲覧"])
        VIEW08(["VIEW-08\nコンタクトページ閲覧"])
        VIEW09(["VIEW-09\n広告閲覧"])

        VIEW01 -->|詳細へ| VIEW03
        VIEW02 -->|詳細へ| VIEW03
        VIEW04 -->|詳細へ| VIEW03
        VIEW03 -->|含む| VIEW05
        VIEW01 -->|含む| VIEW09
        VIEW02 -->|含む| VIEW09
        VIEW03 -->|含む| VIEW09
    end

    READER --> VIEW01
    READER --> VIEW02
    READER --> VIEW03
    READER --> VIEW04
    READER --> VIEW06
    READER --> VIEW07
    READER --> VIEW08
    VIEW09 -.->|広告配信| ADSENSE
    VIEW01 -.->|ホスティング| GITHUB
    VIEW02 -.->|ホスティング| GITHUB
    VIEW03 -.->|ホスティング| GITHUB
    VIEW06 -.->|ホスティング| GITHUB
    VIEW07 -.->|ホスティング| GITHUB
    VIEW08 -.->|ホスティング| GITHUB
```

---

## 7. ユースケース一覧

| UC-ID | ユースケース名 | 主アクター | 概要 |
|---|---|---|---|
| PIPE-01 | 日次パイプライン起動 | OpenClaw Cron | 毎日定時に run_daily.py を起動し当日処理を開始する |
| PIPE-02 | プロット生成 | OpenClaw Cron | Codex CLI でテーマ・登場人物・展開・結末を設計する |
| PIPE-03 | タイトル選定 | OpenClaw Cron | Codex CLI で候補を比較採点し最適タイトルを1件選ぶ |
| PIPE-04 | 本文生成 | OpenClaw Cron | Codex CLI でプロット＋タイトルから 2,000〜5,000字の本文を生成する |
| PIPE-05 | 自動レビュー実行 | OpenClaw Cron | 品質・類似度・禁止語・AdSenseリスクを総合審査する |
| PIPE-06 | 類似度検査 | OpenClaw Cron | 直近90日の作品と 3-gram Jaccard >= 0.40 を検出する |
| PIPE-07 | 禁止語検査 | OpenClaw Cron | banned_terms.json に基づき禁止表現を検出する |
| PIPE-08 | AdSenseリスク検査 | OpenClaw Cron | AdSense ポリシー違反リスクを審査する |
| PIPE-09 | 品質再生成 | OpenClaw Cron | レビュー不合格時に本文を最大3回再生成する |
| PUB-01 | 自動公開開始 | OpenClaw Cron | automatic モードでレビュー合格後即座に publish へ進む |
| PUB-02 | 承認待ち登録 | OpenClaw Cron | manual_review モードで pending/*.pending.json を配置する |
| PUB-03 | 作品承認 | オペレーター | pending_review 状態の作品を承認し publish へ進める |
| PUB-04 | 作品差し戻し | オペレーター | 作品を差し戻し stories/ 正本を修正して再レビューへ進める |
| PUB-05 | 再レビュー実行 | オペレーター | 差し戻し後に初回と同一入力セットで再審査する |
| PUB-06 | publish サブステップ実行 | OpenClaw Cron | 正本検証→派生物同期→インデックス更新→git push→published マークを順実行する |
| PUB-07 | 正本検証 | OpenClaw Cron | stories/ に正本 Markdown が存在することを確認する |
| PUB-08 | 派生物同期 | OpenClaw Cron | stories/ から site/_posts/ へ冪等コピーする |
| PUB-09 | stories_index.json 更新 | OpenClaw Cron | 日付降順でアトミック更新する |
| PUB-10 | Git commit / push | OpenClaw Cron | GitHub Pages へ変更を push して公開する |
| PUB-11 | published マーク | OpenClaw Cron | state.json を stage=done, result=published に更新する |
| REC-01 | パイプライン再開 | OpenClaw Cron / オペレーター | state.json の stage を読み取り失敗地点から再開する |
| REC-02 | plot から再開 | OpenClaw Cron / オペレーター | plot artifact がない場合に generate_plot から再実行する |
| REC-03 | title selection から再開 | OpenClaw Cron / オペレーター | plot artifact のみ存在する場合に select_title から再開する |
| REC-04 | story から再開 | OpenClaw Cron / オペレーター | stories/YYYY/ の正本ドラフト有無を見て story から再開する |
| REC-05 | review から再開 | OpenClaw Cron / オペレーター | 初回と同一入力セットで review を再実行する |
| REC-06 | publish サブステップ冪等再実行 | OpenClaw Cron / オペレーター | publish 中断時に公開サブステップをまとめて再実行する |
| REC-07 | CLI 実行失敗リトライ | OpenClaw Cron | 60秒・300秒待機で最大2回再試行する |
| REC-08 | 失敗通知送信 | OpenClaw Cron | powershell.exe 経由で Windows 通知を送信する |
| VIEW-01 | トップページ閲覧 | 読者 | 最新作プレビューと直近5件カードを閲覧する |
| VIEW-02 | 作品一覧閲覧 | 読者 | 日付降順・タグフィルタで全作品を閲覧する |
| VIEW-03 | 作品詳細閲覧 | 読者 | 本文・メタ情報・AdSense広告が配置された詳細ページを閲覧する |
| VIEW-04 | タグ別一覧閲覧 | 読者 | 特定タグでフィルタした作品一覧を閲覧する |
| VIEW-05 | 前後作品ナビゲーション | 読者 | 作品詳細から前後の公開作品へ移動する |
| VIEW-06 | このサイトについて閲覧 | 読者 | /about/ でサイト方針と AI生成方針を確認する |
| VIEW-07 | プライバシーポリシー閲覧 | 読者 | AdSense 対応のプライバシーポリシーを閲覧する |
| VIEW-08 | コンタクトページ閲覧 | 読者 | 連絡先と問い合わせ導線を閲覧する |
| VIEW-09 | 広告閲覧 | 読者 | Google AdSense の広告（記事上部・下部・一覧下部）を閲覧する |

---

*本ドキュメントは SPEC.md §2（スコープ）、§11（AIエージェント構成）、§15〜19（publish・復旧・フロー）、§21（AdSense）に基づいて設計。*
