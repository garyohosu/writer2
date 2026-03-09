from __future__ import annotations

import json
import re
import shutil
import subprocess
from abc import ABC
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _serialize(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _write_json(path: Path, payload: Any) -> None:
    _ensure_parent(path)
    path.write_text(
        json.dumps(_serialize(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def _json_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict, str)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _parse_frontmatter_value(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("[") or raw.startswith("{") or raw.startswith('"'):
        return json.loads(raw)
    if raw in {"true", "false"}:
        return raw == "true"
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if re.fullmatch(r"-?\d+\.\d+", raw):
        return float(raw)
    return raw


def _slugify(text: str) -> str:
    lowered = text.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return normalized or "story"


def _story_entry_from_story(story: StoryMarkdown) -> StoryEntry:
    return StoryEntry(
        date=story.date,
        slug=story.slug,
        title=story.title,
        summary=story.summary,
        tags=list(story.tags),
        genre=story.genre,
        theme=story.theme,
        character_count=story.character_count,
        reading_time_min=story.reading_time_min,
        review_score=story.review_score,
    )


@dataclass
class ArtifactFlags:
    plot_bundle: bool = False
    story_draft: bool = False
    review_report: bool = False
    pending_entry: bool = False
    site_post_synced: bool = False
    index_updated: bool = False
    git_pushed: bool = False


class PublicationMode(StrEnum):
    automatic = "automatic"
    manual_review = "manual_review"


class Stage(StrEnum):
    start = "start"
    plot = "plot"
    story = "story"
    review = "review"
    pending_review = "pending_review"
    publish = "publish"
    done = "done"


class Result(StrEnum):
    idle = "idle"
    in_progress = "in_progress"
    passed = "passed"
    failed = "failed"
    published = "published"


@dataclass
class State:
    run_date: str
    publication_mode: PublicationMode = PublicationMode.automatic
    stage: Stage = Stage.start
    result: Result = Result.idle
    last_published_slug: str = ""
    current_slug: str = ""
    quality_retry_count: int = 0
    artifacts: ArtifactFlags = field(default_factory=ArtifactFlags)

    @classmethod
    def load(cls, path: str | Path) -> State:
        state_path = Path(path)
        payload = _read_json(state_path)
        if payload is None:
            return cls(run_date=date.today().isoformat())
        return cls(
            run_date=payload["run_date"],
            publication_mode=PublicationMode(payload["publication_mode"]),
            stage=Stage(payload["stage"]),
            result=Result(payload["result"]),
            last_published_slug=payload.get("last_published_slug", ""),
            current_slug=payload.get("current_slug", ""),
            quality_retry_count=payload.get("quality_retry_count", 0),
            artifacts=ArtifactFlags(**payload.get("artifacts", {})),
        )

    def save(self, path: str | Path) -> None:
        _write_json(Path(path), self)

    def is_today_done(self, today: str | None = None) -> bool:
        current_date = today or date.today().isoformat()
        return self.run_date == current_date and self.result == Result.published

    def increment_retry(self) -> None:
        self.quality_retry_count += 1


@dataclass
class PlotBundle:
    date: str
    theme: str
    characters: list[str]
    setting: str
    turning_point: str
    ending: str
    title_candidates: list[str]

    def save(self, path: str | Path) -> None:
        _write_json(Path(path), self)

    @classmethod
    def load(cls, path: str | Path) -> PlotBundle:
        payload = _read_json(Path(path), default={})
        return cls(**payload)


@dataclass
class SelectedTitle:
    date: str
    title: str
    slug: str
    score: float

    def save(self, path: str | Path) -> None:
        _write_json(Path(path), self)

    @classmethod
    def load(cls, path: str | Path) -> SelectedTitle:
        payload = _read_json(Path(path), default={})
        return cls(**payload)


@dataclass
class StoryMarkdown:
    title: str
    date: str
    slug: str
    tags: list[str]
    genre: str
    theme: str
    character_count: int
    reading_time_min: int
    status: str
    summary: str
    ai_generated: bool
    review_score: int
    canonical_source: str
    body: str

    def save(self, path: str | Path) -> None:
        story_path = Path(path)
        _ensure_parent(story_path)
        story_path.write_text(self.to_frontmatter(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> StoryMarkdown:
        story_path = Path(path)
        text = story_path.read_text(encoding="utf-8")
        if text.startswith("---"):
            return cls._from_frontmatter(text)
        payload = json.loads(text)
        return cls(**payload)

    def to_frontmatter(self) -> str:
        metadata = {
            "title": self.title,
            "date": self.date,
            "slug": self.slug,
            "tags": self.tags,
            "genre": self.genre,
            "theme": self.theme,
            "character_count": self.character_count,
            "reading_time_min": self.reading_time_min,
            "status": self.status,
            "summary": self.summary,
            "ai_generated": self.ai_generated,
            "review_score": self.review_score,
            "canonical_source": self.canonical_source,
        }
        lines = ["---"]
        lines.extend(f"{key}: {_json_scalar(value)}" for key, value in metadata.items())
        lines.append("---")
        lines.append(self.body)
        return "\n".join(lines) + "\n"

    @classmethod
    def _from_frontmatter(cls, text: str) -> StoryMarkdown:
        lines = text.splitlines()
        metadata: dict[str, Any] = {}
        body_lines: list[str] = []
        in_body = False
        for line in lines[1:]:
            if line == "---":
                in_body = True
                continue
            if not in_body:
                key, raw_value = line.split(":", 1)
                metadata[key.strip()] = _parse_frontmatter_value(raw_value)
            else:
                body_lines.append(line)
        metadata["body"] = "\n".join(body_lines).rstrip("\n")
        return cls(**metadata)


@dataclass
class ReviewReport:
    slug: str
    review_score: int
    originality: int
    readability: int
    consistency: int
    opening_hook: int
    ending_impression: int
    banned_term_violations: list[str]
    adsense_risk: bool
    similarity_max: float
    similarity_target_slug: str
    passed: bool

    def save(self, path: str | Path) -> None:
        _write_json(Path(path), self)

    def _calculate_score(self) -> int:
        weighted = (
            self.originality * 0.25
            + self.readability * 0.20
            + self.consistency * 0.25
            + self.opening_hook * 0.15
            + self.ending_impression * 0.15
        )
        return round(weighted)


@dataclass
class SimilarityResult:
    max_score: float
    target_slug: str
    exceeded: bool


@dataclass
class StoryEntry:
    date: str
    slug: str
    title: str
    summary: str
    tags: list[str]
    genre: str
    theme: str
    character_count: int
    reading_time_min: int
    review_score: int


@dataclass
class StoriesIndex:
    entries: list[StoryEntry]

    @classmethod
    def load(cls, path: str | Path) -> StoriesIndex:
        payload = _read_json(Path(path), default=[])
        return cls(entries=[StoryEntry(**entry) for entry in payload])

    def save(self, path: str | Path) -> None:
        _write_json(Path(path), self.entries)

    def save_atomic(self, path: str | Path) -> None:
        target_path = Path(path)
        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        _write_json(temp_path, self.entries)
        _ensure_parent(target_path)
        temp_path.replace(target_path)

    def add_or_update(self, story: StoryMarkdown) -> None:
        entry = _story_entry_from_story(story)
        by_slug = {existing.slug: existing for existing in self.entries}
        by_slug[entry.slug] = entry
        self.entries = sorted(by_slug.values(), key=lambda item: item.date, reverse=True)

    def get_recent(self, days: int) -> list[StoryEntry]:
        if not self.entries:
            return []
        anchor = _parse_date(self.entries[0].date)
        cutoff = anchor - timedelta(days=days)
        return [entry for entry in self.entries if _parse_date(entry.date) >= cutoff]

    def get_recent_n(self, n: int) -> list[StoryEntry]:
        return self.entries[: max(0, n)]


@dataclass
class ThemeEntry:
    theme: str
    date: str


@dataclass
class UsedThemes:
    entries: list[ThemeEntry]
    window_days: int = 90

    @classmethod
    def load(cls, path: str | Path) -> UsedThemes:
        payload = _read_json(Path(path), default={"entries": [], "window_days": 90})
        entries = [ThemeEntry(**entry) for entry in payload.get("entries", [])]
        return cls(entries=entries, window_days=payload.get("window_days", 90))

    def save(self, path: str | Path) -> None:
        _write_json(Path(path), {"entries": self.entries, "window_days": self.window_days})

    def add(self, theme: str, date: str) -> None:
        self.entries.append(ThemeEntry(theme=theme, date=date))
        self.prune_old()

    def get_recent(self, days: int) -> list[str]:
        if not self.entries:
            return []
        anchor = max(_parse_date(entry.date) for entry in self.entries)
        cutoff = anchor - timedelta(days=days)
        return [entry.theme for entry in self.entries if _parse_date(entry.date) >= cutoff]

    def prune_old(self) -> None:
        if not self.entries:
            return
        anchor = max(_parse_date(entry.date) for entry in self.entries)
        cutoff = anchor - timedelta(days=self.window_days)
        self.entries = [entry for entry in self.entries if _parse_date(entry.date) >= cutoff]


@dataclass
class BannedTerms:
    terms: list[str]

    @classmethod
    def load(cls, path: str | Path) -> BannedTerms:
        payload = _read_json(Path(path), default={"terms": []})
        if isinstance(payload, dict):
            return cls(terms=payload.get("terms", []))
        return cls(terms=list(payload))

    def check(self, text: str) -> list[str]:
        lowered = text.lower()
        return [term for term in self.terms if term.lower() in lowered]


@dataclass
class ContextBundle:
    run_date: str
    recent_summaries: list[str]
    used_themes_snapshot: list[str]
    style_notes: str
    review_input_cache: dict

    @classmethod
    def build(cls, date: str, index: StoriesIndex, themes: UsedThemes) -> ContextBundle:
        return cls(
            run_date=date,
            recent_summaries=[entry.summary for entry in index.get_recent_n(5)],
            used_themes_snapshot=themes.get_recent(themes.window_days),
            style_notes="Keep the prose concise and avoid imitation.",
            review_input_cache={},
        )

    def save(self, path: str | Path) -> None:
        _write_json(Path(path), self)

    @classmethod
    def load(cls, path: str | Path) -> ContextBundle:
        payload = _read_json(Path(path), default={})
        return cls(**payload)


@dataclass
class PendingEntry:
    slug: str
    canonical_path: str
    review_summary: str
    created_at: str

    def save(self, path: str | Path) -> None:
        _write_json(Path(path), self)

    @classmethod
    def load(cls, path: str | Path) -> PendingEntry:
        payload = _read_json(Path(path), default={})
        return cls(**payload)


@dataclass
class CodexCLI:
    model: str = "gpt-5.4"

    def execute(self, prompt_file: str) -> str:
        return self.execute_inline(Path(prompt_file).read_text(encoding="utf-8"))

    def execute_inline(self, prompt: str) -> str:
        return prompt


@dataclass
class GitClient:
    repo_path: str

    def commit(self, message: str) -> None:
        subprocess.run(["git", "-C", self.repo_path, "commit", "-am", message], check=True)

    def push(self) -> None:
        subprocess.run(["git", "-C", self.repo_path, "push"], check=True)

    def is_clean(self) -> bool:
        result = subprocess.run(
            ["git", "-C", self.repo_path, "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == ""


@dataclass
class WindowsNotifier:
    ps1_path: str

    def notify(self, title: str, message: str) -> None:
        script_path = Path(self.ps1_path)
        if not script_path.exists():
            return
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-File",
                str(script_path),
                "-Title",
                title,
                "-Message",
                message,
            ],
            check=False,
        )


@dataclass
class BaseAgent(ABC):
    codex_cli: CodexCLI
    max_retries: int = 2
    retry_wait_seconds: list[int] = field(default_factory=lambda: [60, 300])

    def execute(self, prompt: str) -> str:
        return self._run_with_retry(prompt)

    def _run_with_retry(self, prompt: str) -> str:
        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                return self.codex_cli.execute_inline(prompt)
            except Exception as exc:  # pragma: no cover - integration path
                last_error = exc
        if last_error is None:
            raise RuntimeError("Agent execution failed without an exception.")
        raise last_error


@dataclass
class PlotAgent(BaseAgent):
    used_themes: UsedThemes = field(default_factory=lambda: UsedThemes(entries=[]))
    banned_terms: BannedTerms = field(default_factory=lambda: BannedTerms(terms=[]))

    def generate_plot(self, run_date: str) -> PlotBundle:
        recent = set(self.used_themes.get_recent(self.used_themes.window_days))
        theme_candidates = [
            "small wonder after work",
            "quiet cat mystery",
            "gentle commuter fantasy",
            "light station SF",
        ]
        theme = next((candidate for candidate in theme_candidates if candidate not in recent), theme_candidates[0])
        self.used_themes.add(theme, run_date)
        titles = [
            f"{run_date} midnight cat",
            f"{run_date} after work wonder",
            f"{run_date} station lantern",
        ]
        return PlotBundle(
            date=run_date,
            theme=theme,
            characters=["A tired engineer", "A silent cat"],
            setting="A city apartment lobby after midnight",
            turning_point="The elevator opens to a floor that should not exist",
            ending="The cat disappears, leaving the engineer calmer than before",
            title_candidates=[title for title in titles if not self.banned_terms.check(title)],
        )


@dataclass
class TitleSelectionAgent(BaseAgent):
    def select_title(self, plot: PlotBundle) -> SelectedTitle:
        scores = self._score_candidates(plot.title_candidates, plot)
        title = max(scores, key=scores.get)
        tail = _slugify(title.replace(plot.date, "").strip())
        slug = plot.date if not tail else f"{plot.date}-{tail}"
        return SelectedTitle(date=plot.date, title=title, slug=slug, score=scores[title])

    def _score_candidates(self, candidates: list[str], plot: PlotBundle) -> dict:
        theme_words = set(plot.theme.split())
        scores: dict[str, float] = {}
        for candidate in candidates:
            overlap = sum(1 for word in candidate.split() if word in theme_words)
            scores[candidate] = float(overlap + max(1, 20 - len(candidate)))
        return scores


@dataclass
class StoryAgent(BaseAgent):
    def generate_story(self, plot: PlotBundle, title: SelectedTitle, context: ContextBundle) -> StoryMarkdown:
        body = (
            f"{title.title}\n\n"
            f"{plot.characters[0]} waits in {plot.setting}. "
            f"{plot.turning_point}. {plot.ending}. "
            f"Recent echoes: {'; '.join(context.recent_summaries[:2]) or 'none'}."
        )
        return StoryMarkdown(
            title=title.title,
            date=title.date,
            slug=title.slug,
            tags=["daily", "fiction"],
            genre="short",
            theme=plot.theme,
            character_count=self._count_characters(body),
            reading_time_min=max(1, self._count_characters(body) // 600 + 1),
            status="pending_review",
            summary=f"A short story about {plot.characters[0].lower()} and a quiet cat.",
            ai_generated=True,
            review_score=0,
            canonical_source="stories",
            body=body,
        )

    def _build_prompt(self, plot: PlotBundle, title: SelectedTitle, context: ContextBundle) -> str:
        return (
            f"Write a short story titled {title.title}. "
            f"Theme: {plot.theme}. Context: {' | '.join(context.recent_summaries)}"
        )

    def _count_characters(self, text: str) -> int:
        return len(text)


@dataclass
class SimilarityChecker:
    threshold: float = 0.40
    window_days: int = 90

    def check(self, story: StoryMarkdown, index: StoriesIndex) -> SimilarityResult:
        source_text = f"{story.title} {story.summary}".strip()
        source_ngrams = self._build_ngrams(source_text, 3)
        story_date = _parse_date(story.date)

        max_score = 0.0
        target_slug = ""
        for entry in index.entries:
            if story_date - _parse_date(entry.date) > timedelta(days=self.window_days):
                continue
            candidate_text = f"{entry.title} {entry.summary}".strip()
            score = self._jaccard(source_ngrams, self._build_ngrams(candidate_text, 3))
            if score > max_score:
                max_score = score
                target_slug = entry.slug

        return SimilarityResult(
            max_score=max_score,
            target_slug=target_slug,
            exceeded=max_score >= self.threshold,
        )

    def _build_ngrams(self, text: str, n: int) -> set[str]:
        compact = re.sub(r"\s+", " ", text).strip()
        if not compact:
            return set()
        if len(compact) <= n:
            return {compact}
        return {compact[index : index + n] for index in range(len(compact) - n + 1)}

    def _jaccard(self, a: set, b: set) -> float:
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)


@dataclass
class ReviewAgent(BaseAgent):
    banned_terms: BannedTerms = field(default_factory=lambda: BannedTerms(terms=[]))
    similarity_checker: SimilarityChecker = field(default_factory=SimilarityChecker)

    def review(
        self,
        story: StoryMarkdown,
        index: StoriesIndex,
        mode: PublicationMode,
        instruction: str,
    ) -> ReviewReport:
        similarity = self.similarity_checker.check(story, index)
        violations = self._check_banned_terms(story)
        adsense_risk = self._check_adsense_risk(story)
        originality = max(0, 100 - round(similarity.max_score * 100))
        readability = 85 if story.character_count >= 50 else 70
        consistency = 85 if story.title and story.body else 60
        opening_hook = 85 if story.body[:80].strip() else 60
        ending_impression = 85 if story.body.strip() else 60
        if mode == PublicationMode.manual_review and instruction:
            ending_impression = min(100, ending_impression + 5)

        report = ReviewReport(
            slug=story.slug,
            review_score=0,
            originality=originality,
            readability=readability,
            consistency=consistency,
            opening_hook=opening_hook,
            ending_impression=ending_impression,
            banned_term_violations=violations,
            adsense_risk=adsense_risk,
            similarity_max=similarity.max_score,
            similarity_target_slug=similarity.target_slug,
            passed=False,
        )
        report.review_score = report._calculate_score()
        report.passed = (
            report.originality >= 80
            and report.readability >= 75
            and report.consistency >= 85
            and report.review_score >= 80
            and not report.banned_term_violations
            and not report.adsense_risk
            and not similarity.exceeded
        )
        return report

    def _check_adsense_risk(self, story: StoryMarkdown) -> bool:
        risky_words = {"explicit", "violence", "gambling"}
        lowered = f"{story.summary} {story.body}".lower()
        return any(word in lowered for word in risky_words)

    def _check_banned_terms(self, story: StoryMarkdown) -> list[str]:
        return self.banned_terms.check(f"{story.title}\n{story.summary}\n{story.body}")


@dataclass
class PublishAgent:
    stories_dir: str
    site_posts_dir: str
    index_path: str
    git_client: GitClient | None = None

    def validate_canonical_story(self, slug: str) -> bool:
        return self._find_story_path(slug) is not None

    def sync_site_post(self, slug: str) -> Path:
        story_path = self._find_story_path(slug)
        if story_path is None:
            raise FileNotFoundError(f"Canonical story not found for slug: {slug}")

        target_path = Path(self.site_posts_dir) / self._site_post_name(slug)
        _ensure_parent(target_path)
        shutil.copyfile(story_path, target_path)
        return target_path

    def update_story_index(self, story: StoryMarkdown) -> None:
        index = StoriesIndex.load(self.index_path)
        index.add_or_update(story)
        index.save_atomic(self.index_path)

    def git_commit_push(self, slug: str) -> None:
        if self.git_client is None:
            return
        self.git_client.commit(f"Publish {slug}")
        self.git_client.push()

    def mark_published(self, state: State) -> None:
        state.stage = Stage.done
        state.result = Result.published
        state.last_published_slug = state.current_slug

    def _find_story_path(self, slug: str) -> Path | None:
        base = Path(self.stories_dir)
        for path in base.rglob(f"{slug}.md"):
            return path
        return None

    def _site_post_name(self, slug: str) -> str:
        if re.match(r"^\d{4}-\d{2}-\d{2}-", slug):
            return f"{slug}.md"
        return f"{date.today().isoformat()}-{slug}.md"


class RunDaily:
    run_date: str
    state: State

    def __init__(
        self,
        run_date: str | None = None,
        state: State | None = None,
        state_path: str | Path = "data/state.json",
        plot_agent: PlotAgent | None = None,
        title_agent: TitleSelectionAgent | None = None,
        story_agent: StoryAgent | None = None,
        review_agent: ReviewAgent | None = None,
        publish_agent: PublishAgent | None = None,
        notifier: WindowsNotifier | None = None,
    ) -> None:
        self.run_date = run_date or date.today().isoformat()
        self.state_path = Path(state_path)
        self.state = state or State.load(self.state_path)
        self.codex_cli = CodexCLI()
        self.used_themes = UsedThemes(entries=[])
        self.banned_terms = BannedTerms(terms=[])
        self.plot_agent = plot_agent or PlotAgent(
            codex_cli=self.codex_cli,
            used_themes=self.used_themes,
            banned_terms=self.banned_terms,
        )
        self.title_agent = title_agent or TitleSelectionAgent(codex_cli=self.codex_cli)
        self.story_agent = story_agent or StoryAgent(codex_cli=self.codex_cli)
        self.review_agent = review_agent or ReviewAgent(
            codex_cli=self.codex_cli,
            banned_terms=self.banned_terms,
            similarity_checker=SimilarityChecker(),
        )
        self.publish_agent = publish_agent or PublishAgent(
            stories_dir="stories",
            site_posts_dir="site/_posts",
            index_path="data/stories_index.json",
        )
        self.notifier = notifier or WindowsNotifier("scripts/notify_failure.ps1")

    def run(self) -> State:
        if self.state.is_today_done(self.run_date):
            return self.state
        try:
            return self.resume_from_state()
        except Exception as exc:
            self.state.result = Result.failed
            self.notify_failure(str(exc))
            self.state.save(self.state_path)
            raise

    def resume_from_state(self) -> State:
        if self.state.stage == Stage.start:
            self.state.run_date = self.run_date
            self.state.stage = Stage.plot
            self.state.result = Result.in_progress
        self.state.save(self.state_path)
        return self.state

    def notify_failure(self, message: str) -> None:
        self.notifier.notify("DailyShortStorySite failure", message)
