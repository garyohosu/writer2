# UI.md
## 1日1冊短編小説サイト — ユーザーインターフェース設計

**Project:** DailyShortStorySite
**Version:** 1.2.0
**作成日:** 2026-03-09
**Publishing Target:** `https://garyohosu.github.io/writer`

---

## 1. サイト構造（ページ一覧）

```mermaid
graph TD
    ROOT["/ (ルート)\nトップページ\n最新作 + 一覧プレビュー"]
    INDEX["/posts/\n作品一覧ページ\n日付降順・タグフィルタ"]
    STORY["/posts/:slug/\n作品詳細ページ\n本文・AdSense"]
    ABOUT["/about/\nサイト概要\nAI生成明記"]
    PRIVACY["/privacy-policy/\nプライバシーポリシー\nAdSense必須"]
    CONTACT["/contact/\nコンタクト\nAdSense必須"]
    TAG["/tags/:tag/\nタグ別一覧"]

    ROOT --> INDEX
    ROOT --> STORY
    ROOT --> ABOUT
    ROOT --> PRIVACY
    ROOT --> CONTACT
    INDEX --> STORY
    INDEX --> TAG
    TAG --> STORY
```

---

## 2. ナビゲーション構成

```mermaid
graph LR
    NAV["グローバルナビゲーション\n（全ページ共通ヘッダー）"]

    NAV --> HOME["🏠 ホーム\n/writer/"]
    NAV --> STORIES["📚 作品一覧\n/writer/posts/"]
    NAV --> ABOUT2["ℹ️ このサイトについて\n/writer/about/"]
    NAV --> FOOTER["フッターリンク群"]

    FOOTER --> PRIVACY2["プライバシーポリシー"]
    FOOTER --> CONTACT2["コンタクト"]
    FOOTER --> AIDISCL["AI生成作品である旨の表示"]
```

---

## 3. トップページ レイアウト

```mermaid
graph TD
    subgraph TOP["トップページ /writer/"]
        direction TB
        H["ヘッダー\nサイトタイトル + ナビゲーション"]
        HERO["ヒーローエリア\n本日の作品タイトル・要約・読む"]
        AD1["【広告枠①】記事上部\nAdSense"]
        LATEST["最新作プレビュー（本文冒頭）"]
        AD2["【広告枠②】記事下部\nAdSense"]
        RECENT["最近の作品カード一覧\n（直近5件）"]
        AD3["【広告枠③】一覧下部\nAdSense"]
        FOOT["フッター\nAI生成明記 / プライバシー / コンタクト"]

        H --> HERO --> AD1 --> LATEST --> AD2 --> RECENT --> AD3 --> FOOT
    end
```

---

## 4. 作品一覧ページ レイアウト

```mermaid
graph TD
    subgraph LIST["作品一覧 /writer/posts/"]
        direction TB
        LH["ヘッダー + ナビ"]
        LTITLE["ページタイトル「作品一覧」"]
        LTAG["タグフィルタ（猫 / 日常 / SF / ファンタジー…）"]
        LCARDS["作品カード列（日付降順）\n各カード: タイトル / 要約 / 読了時間 / タグ"]
        LAD["【広告枠③】一覧下部\nAdSense"]
        LPAGER["ページネーション"]
        LFOOT["フッター"]

        LH --> LTITLE --> LTAG --> LCARDS --> LAD --> LPAGER --> LFOOT
    end
```

---

## 5. 作品詳細ページ レイアウト

```mermaid
graph TD
    subgraph DETAIL["作品詳細 /writer/posts/:slug/"]
        direction TB
        DH["ヘッダー + ナビ"]
        DMETA["メタ情報\n日付 / ジャンル / タグ / 読了時間 / 文字数"]
        DAD1["【広告枠①】記事上部\nAdSense"]
        DBODY["本文\n（Markdown レンダリング）"]
        DAD2["【広告枠②】記事下部\nAdSense"]
        DTAGS["タグリンク"]
        DPREV["← 前の作品 / 次の作品 →"]
        DFOOT["フッター\nAI生成作品である旨の表示"]

        DH --> DMETA --> DAD1 --> DBODY --> DAD2 --> DTAGS --> DPREV --> DFOOT
    end
```

---

## 6. 日次パイプライン フロー（自動運用 / automatic）

```mermaid
flowchart TD
    CRON["OpenClaw Cron\n毎日定時起動"]
    LOAD["state.json 読み込み"]
    CHECK{当日処理済み？\nresult=published}

    CRON --> LOAD --> CHECK
    CHECK -- "YES → スキップ" --> END["終了"]
    CHECK -- "NO" --> STAGE{stage 判定}

    STAGE -- "start / plot" --> PLOT["Plot Agent\nテーマ生成 → タイトル選定\nartifacts/plot/ に保存"]
    STAGE -- "story" --> STORY_GEN
    STAGE -- "review" --> REVIEW_EXEC
    STAGE -- "publish (復旧)" --> PUBLISH

    PLOT --> STORY_GEN["Story Agent\nプロット+タイトルから本文生成\nstories/ に正本保存"]
    STORY_GEN --> REVIEW_EXEC["Review Agent\n品質・類似度・禁止語・AdSense リスク検査"]

    REVIEW_EXEC --> JUDGE{合格？\nscore >= 80}
    JUDGE -- "不合格 (retry < 3)" --> STORY_GEN
    JUDGE -- "3回失敗" --> FAIL["result=failed\nWindows通知 + ログ保存"]
    JUDGE -- "合格" --> PUBLISH

    PUBLISH["Publish Agent\npublish 開始時\nstage=publish, result=in_progress"]
    PUBLISH --> SYNC["sync_site_post\nstories/ → site/_posts/"]
    SYNC --> IDX["update_story_index\nstories_index.json 更新\n（アトミック更新）"]
    IDX --> GIT["git_commit_push"]
    GIT --> DONE["mark_published\nstage=done, result=published"]
    DONE --> END
```

---

## 7. 障害復旧フロー

```mermaid
flowchart TD
    RESTART["手動 or cron 再実行"]
    READ["state.json 読み込み"]

    RESTART --> READ --> STAGE2{stage}

    STAGE2 -- "plot\nplot.json あり\ntitle.json なし" --> TITLE_RESUME["Title Selection から再開"]
    STAGE2 -- "plot\n両方なし" --> PLOT_RESUME["Plot から再開"]
    STAGE2 -- "story" --> STORY_RESUME["正本ドラフト有無で判断\n→ 再生成 or 継続"]
    STAGE2 -- "review" --> REVIEW_RESUME["同一入力で再レビュー"]
    STAGE2 -- "publish" --> PUBLISH_RESUME["公開サブステップを\n冪等再実行\n（sync→index→git→mark）"]
    STAGE2 -- "done / published" --> SKIP["当日スキップ"]

    TITLE_RESUME --> CONTINUE["通常フローへ合流"]
    PLOT_RESUME --> CONTINUE
    STORY_RESUME --> CONTINUE
    REVIEW_RESUME --> CONTINUE
    PUBLISH_RESUME --> CONTINUE
```

---

## 8. AdSense 広告枠 配置まとめ

| 枠番号 | 配置場所 | 対象ページ |
|---|---|---|
| ① 記事上部 | 記事メタ情報の直下、本文開始前 | トップ / 作品詳細 |
| ② 記事下部 | 本文終了直後、タグリンク前 | 作品詳細 |
| ③ 一覧下部 | 作品カード一覧の末尾、ページネーション前 | トップ / 作品一覧 |

---

## 9. URL 設計まとめ

```mermaid
graph LR
    BASE["https://garyohosu.github.io/writer"]
    BASE --> R["/  → トップ"]
    BASE --> P["/posts/  → 一覧"]
    BASE --> PS["/posts/:slug/  → 詳細"]
    BASE --> A["/about/"]
    BASE --> PV["/privacy-policy/"]
    BASE --> C["/contact/"]
    BASE --> T["/tags/:tag/"]
```

- 内部リンクは常に `{{ site.baseurl }}/posts/:slug/` 形式で生成
- `canonical` および OGP URL は `{{ site.url }}{{ site.baseurl }}{{ page.url }}`
- ルート相対 `/posts/...` の直書き禁止（§20.2）

---

*本ドキュメントは SPEC.md §20〜21 の要件に基づいて設計した。実装時は Chirpy テーマの `_layouts/` / `_includes/` と突き合わせて調整すること。*
