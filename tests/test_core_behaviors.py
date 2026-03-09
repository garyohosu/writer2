from __future__ import annotations

from pathlib import Path

from daily_short_story import (
    ArtifactFlags,
    PendingEntry,
    PublicationMode,
    PublishAgent,
    Result,
    SimilarityChecker,
    Stage,
    State,
    StoriesIndex,
    StoryEntry,
    StoryMarkdown,
)


def make_story(
    *,
    date: str,
    slug: str,
    title: str = "Midnight Cat",
    summary: str = "A tired engineer meets a cat in the lobby.",
    body: str = "A tired engineer meets a cat in the lobby and follows it home.",
    review_score: int = 86,
) -> StoryMarkdown:
    return StoryMarkdown(
        title=title,
        date=date,
        slug=slug,
        tags=["cat", "daily"],
        genre="short",
        theme="small wonder",
        character_count=len(body),
        reading_time_min=3,
        status="pending_review",
        summary=summary,
        ai_generated=True,
        review_score=review_score,
        canonical_source="stories",
        body=body,
    )


def test_state_roundtrip_and_retry_counter(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = State(
        run_date="2026-03-09",
        publication_mode=PublicationMode.automatic,
        stage=Stage.review,
        result=Result.in_progress,
        last_published_slug="2026-03-08-rain-window",
        current_slug="2026-03-09-midnight-cat",
        quality_retry_count=0,
        artifacts=ArtifactFlags(plot_bundle=True, story_draft=True),
    )

    state.increment_retry()
    state.save(path)
    loaded = State.load(path)

    assert loaded.quality_retry_count == 1
    assert loaded.current_slug == "2026-03-09-midnight-cat"
    assert loaded.artifacts.story_draft is True


def test_stories_index_add_or_update_keeps_date_descending_order() -> None:
    index = StoriesIndex(entries=[])
    older = make_story(date="2026-03-08", slug="2026-03-08-rain-window")
    newer = make_story(date="2026-03-09", slug="2026-03-09-midnight-cat")

    index.add_or_update(older)
    index.add_or_update(newer)
    index.add_or_update(
        make_story(
            date="2026-03-08",
            slug="2026-03-08-rain-window",
            summary="Updated summary",
            review_score=90,
        )
    )

    assert [entry.slug for entry in index.entries] == [
        "2026-03-09-midnight-cat",
        "2026-03-08-rain-window",
    ]
    assert index.entries[1].summary == "Updated summary"
    assert [entry.slug for entry in index.get_recent_n(1)] == ["2026-03-09-midnight-cat"]


def test_similarity_checker_detects_recent_overlap() -> None:
    checker = SimilarityChecker(threshold=0.40, window_days=90)
    index = StoriesIndex(
        entries=[
            StoryEntry(
                date="2026-03-01",
                slug="2026-03-01-midnight-cat",
                title="Midnight Cat",
                summary="A tired engineer meets a cat in the lobby.",
                tags=["cat"],
                genre="short",
                theme="small wonder",
                character_count=1200,
                reading_time_min=3,
                review_score=85,
            )
        ]
    )

    result = checker.check(
        make_story(
            date="2026-03-09",
            slug="2026-03-09-midnight-cat-2",
            title="Midnight Cat",
            summary="A tired engineer meets a cat in the lobby.",
        ),
        index,
    )

    assert result.exceeded is True
    assert result.target_slug == "2026-03-01-midnight-cat"
    assert result.max_score >= 0.40


def test_publish_agent_syncs_canonical_story_and_updates_index(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    site_posts_dir = tmp_path / "site" / "_posts"
    index_path = tmp_path / "data" / "stories_index.json"

    story = make_story(date="2026-03-09", slug="2026-03-09-midnight-cat")
    canonical_path = stories_dir / "2026" / f"{story.slug}.md"
    canonical_path.parent.mkdir(parents=True)
    canonical_path.write_text(story.to_frontmatter(), encoding="utf-8")

    agent = PublishAgent(
        stories_dir=str(stories_dir),
        site_posts_dir=str(site_posts_dir),
        index_path=str(index_path),
    )

    assert agent.validate_canonical_story(story.slug) is True

    synced_path = agent.sync_site_post(story.slug)
    agent.update_story_index(story)

    assert synced_path.name == "2026-03-09-midnight-cat.md"
    assert synced_path.read_text(encoding="utf-8").startswith("---")

    saved_index = StoriesIndex.load(index_path)
    assert [entry.slug for entry in saved_index.entries] == [story.slug]


def test_pending_entry_roundtrip(tmp_path: Path) -> None:
    entry = PendingEntry(
        slug="2026-03-09-midnight-cat",
        canonical_path="stories/2026/2026-03-09-midnight-cat.md",
        review_summary="Looks good after review.",
        created_at="2026-03-09T07:00:00Z",
    )
    path = tmp_path / "pending" / "2026-03-09-midnight-cat.pending.json"
    entry.save(path)

    loaded = PendingEntry.load(path)

    assert loaded.slug == entry.slug
    assert loaded.canonical_path == entry.canonical_path
    assert loaded.review_summary == entry.review_summary


def test_state_is_today_done_only_when_published_for_today() -> None:
    done_state = State(
        run_date="2026-03-09",
        publication_mode=PublicationMode.automatic,
        stage=Stage.done,
        result=Result.published,
        last_published_slug="2026-03-09-midnight-cat",
        current_slug="2026-03-09-midnight-cat",
        quality_retry_count=0,
        artifacts=ArtifactFlags(),
    )
    not_done_state = State(
        run_date="2026-03-08",
        publication_mode=PublicationMode.automatic,
        stage=Stage.done,
        result=Result.published,
        last_published_slug="2026-03-08-rain-window",
        current_slug="2026-03-08-rain-window",
        quality_retry_count=0,
        artifacts=ArtifactFlags(),
    )

    assert done_state.is_today_done("2026-03-09") is True
    assert not_done_state.is_today_done("2026-03-09") is False
