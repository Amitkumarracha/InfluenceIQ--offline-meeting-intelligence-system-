"""
Tests for Phase 7 — Audio–PPT cross-modal alignment.

All tests use small synthetic in-memory data.
No real meeting files are downloaded or required.
No alignment accuracy is claimed from synthetic tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Synthetic helpers
# ---------------------------------------------------------------------------

def _make_slide_ids(n: int) -> list[str]:
    return [f"slide_{i+1:02d}" for i in range(n)]


def _make_random_embeddings(n_slides: int, dim: int = 8, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((n_slides, dim)).astype(np.float32)


def _make_transcript_segment(
    segment_id: int = 1,
    start: float = 10.0,
    end: float = 20.0,
    speaker: str = "SPEAKER_01",
    text: str = "We use a smaller model to reduce computational cost.",
):
    from src.audio.asr import TranscriptSegment
    return TranscriptSegment(
        segment_id=segment_id,
        start=start,
        end=end,
        speaker=speaker,
        text=text,
    )


# ---------------------------------------------------------------------------
# 1. Temporal overlap calculation
# ---------------------------------------------------------------------------

class TestTemporalOverlap:
    def test_full_overlap(self):
        from src.fusion.temporal_alignment import compute_overlap_seconds
        assert compute_overlap_seconds(10, 20, 5, 25) == pytest.approx(10.0)

    def test_partial_overlap(self):
        from src.fusion.temporal_alignment import compute_overlap_seconds
        assert compute_overlap_seconds(10, 20, 15, 30) == pytest.approx(5.0)

    def test_no_overlap(self):
        from src.fusion.temporal_alignment import compute_overlap_seconds
        assert compute_overlap_seconds(10, 20, 25, 35) == pytest.approx(0.0)

    def test_segment_contained_in_slide(self):
        from src.fusion.temporal_alignment import compute_overlap_seconds
        assert compute_overlap_seconds(12, 18, 10, 20) == pytest.approx(6.0)

    def test_slide_contained_in_segment(self):
        from src.fusion.temporal_alignment import compute_overlap_seconds
        assert compute_overlap_seconds(5, 30, 10, 20) == pytest.approx(10.0)

    def test_adjacent_no_overlap(self):
        from src.fusion.temporal_alignment import compute_overlap_seconds
        assert compute_overlap_seconds(10, 20, 20, 30) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 2. Temporal score (normalised)
# ---------------------------------------------------------------------------

class TestTemporalScore:
    def test_score_full_overlap(self):
        from src.fusion.temporal_alignment import SlideTimingInfo, temporal_score_for_slide
        timing = SlideTimingInfo("slide_01", start_time=0.0, end_time=30.0)
        result = temporal_score_for_slide(5.0, 15.0, timing)
        assert result.score == pytest.approx(1.0)
        assert result.timing_available is True

    def test_score_half_overlap(self):
        from src.fusion.temporal_alignment import SlideTimingInfo, temporal_score_for_slide
        timing = SlideTimingInfo("slide_01", start_time=15.0, end_time=30.0)
        result = temporal_score_for_slide(10.0, 20.0, timing)  # 5s overlap / 10s seg
        assert result.score == pytest.approx(0.5)

    def test_score_no_timing(self):
        from src.fusion.temporal_alignment import SlideTimingInfo, temporal_score_for_slide
        timing = SlideTimingInfo("slide_01")   # no start/end
        result = temporal_score_for_slide(10.0, 20.0, timing)
        assert result.score is None
        assert result.timing_available is False

    def test_score_clipped_at_one(self):
        # Segment fully inside slide — score must be exactly 1.0
        from src.fusion.temporal_alignment import SlideTimingInfo, temporal_score_for_slide
        timing = SlideTimingInfo("slide_01", start_time=0.0, end_time=100.0)
        result = temporal_score_for_slide(10.0, 20.0, timing)
        assert result.score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 3. No temporal information handling
# ---------------------------------------------------------------------------

class TestNoTiming:
    def test_has_any_timing_false(self):
        from src.fusion.temporal_alignment import SlideTimingInfo, has_any_timing
        timings = [SlideTimingInfo(f"slide_{i:02d}") for i in range(5)]
        assert has_any_timing(timings) is False

    def test_has_any_timing_true(self):
        from src.fusion.temporal_alignment import SlideTimingInfo, has_any_timing
        timings = [
            SlideTimingInfo("slide_01"),
            SlideTimingInfo("slide_02", start_time=30.0, end_time=60.0),
        ]
        assert has_any_timing(timings) is True

    def test_compute_temporal_scores_all_none(self):
        from src.fusion.temporal_alignment import SlideTimingInfo, compute_temporal_scores
        timings = [SlideTimingInfo(f"slide_{i:02d}") for i in range(3)]
        results = compute_temporal_scores(10.0, 20.0, timings)
        assert all(r.score is None for r in results)
        assert all(not r.timing_available for r in results)


# ---------------------------------------------------------------------------
# 4. Cosine similarity
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        from src.fusion.semantic_alignment import cosine_similarity_matrix
        v = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        scores = cosine_similarity_matrix(v[0], v)
        assert scores[0] == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_vectors(self):
        from src.fusion.semantic_alignment import cosine_similarity_matrix
        q = np.array([1.0, 0.0], dtype=np.float32)
        k = np.array([[0.0, 1.0]], dtype=np.float32)
        scores = cosine_similarity_matrix(q, k)
        assert scores[0] == pytest.approx(0.0, abs=1e-5)

    def test_zero_query_vector(self):
        from src.fusion.semantic_alignment import cosine_similarity_matrix
        q = np.zeros(4, dtype=np.float32)
        k = np.ones((3, 4), dtype=np.float32)
        scores = cosine_similarity_matrix(q, k)
        # Should not raise; scores may be 0 or any finite value
        assert scores.shape == (3,)
        assert np.all(np.isfinite(scores))

    def test_batch_scores(self):
        from src.fusion.semantic_alignment import cosine_similarity_matrix
        rng = np.random.default_rng(0)
        q = rng.random(16).astype(np.float32)
        k = rng.random((10, 16)).astype(np.float32)
        scores = cosine_similarity_matrix(q, k)
        assert scores.shape == (10,)
        assert np.all(scores >= -1.0 - 1e-5)
        assert np.all(scores <= 1.0 + 1e-5)


# ---------------------------------------------------------------------------
# 5. Combined score calculation
# ---------------------------------------------------------------------------

class TestCombineScores:
    def test_equal_weights(self):
        from src.fusion.multimodal_representation import combine_scores
        result = combine_scores(0.8, 0.6, 0.5, 0.5)
        assert result == pytest.approx(0.7)

    def test_temporal_only_weight(self):
        from src.fusion.multimodal_representation import combine_scores
        result = combine_scores(0.9, 0.3, 1.0, 0.0)
        assert result == pytest.approx(0.9)

    def test_semantic_only_weight(self):
        from src.fusion.multimodal_representation import combine_scores
        result = combine_scores(0.9, 0.4, 0.0, 1.0)
        assert result == pytest.approx(0.4)

    def test_no_temporal_falls_back_to_semantic(self):
        from src.fusion.multimodal_representation import combine_scores
        # When temporal_score is None, semantic score gets full normalised weight
        result = combine_scores(None, 0.75, 0.5, 0.5)
        assert result == pytest.approx(0.75)

    def test_no_temporal_zero_semantic(self):
        from src.fusion.multimodal_representation import combine_scores
        result = combine_scores(None, 0.0, 0.5, 0.5)
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 6. Confidence labelling
# ---------------------------------------------------------------------------

class TestConfidenceLabel:
    def test_high(self):
        from src.fusion.multimodal_representation import label_confidence
        assert label_confidence(0.75, 0.5) == "high"

    def test_medium(self):
        from src.fusion.multimodal_representation import label_confidence
        assert label_confidence(0.55, 0.5) == "medium"

    def test_low(self):
        from src.fusion.multimodal_representation import label_confidence
        assert label_confidence(0.3, 0.5) == "low"

    def test_boundary_is_medium(self):
        from src.fusion.multimodal_representation import label_confidence
        assert label_confidence(0.5, 0.5) == "medium"


# ---------------------------------------------------------------------------
# 7. Top-k selection
# ---------------------------------------------------------------------------

class TestTopK:
    def _run_align(self, segment_text, slide_texts, timings=None, top_k=3, threshold=0.0):
        """Helper: run align_segment with a tiny stub embedding model."""
        from src.fusion.multimodal_representation import align_segment
        from src.fusion.temporal_alignment import SlideTimingInfo
        from src.audio.asr import TranscriptSegment

        n = len(slide_texts)
        slide_ids = _make_slide_ids(n)
        rng = np.random.default_rng(7)
        embeddings = rng.random((n, 8)).astype(np.float32)

        if timings is None:
            slide_timings = [SlideTimingInfo(sid) for sid in slide_ids]
        else:
            slide_timings = timings

        seg = TranscriptSegment(1, 0.0, 5.0, "SPEAKER_01", segment_text)

        class StubModel:
            def encode(self, texts, **kw):
                rng2 = np.random.default_rng(sum(ord(c) for c in texts[0]))
                return rng2.random((len(texts), 8)).astype(np.float32)
            def get_sentence_embedding_dimension(self):
                return 8

        return align_segment(
            segment=seg,
            slide_ids=slide_ids,
            slide_timings=slide_timings,
            slide_embeddings=embeddings,
            embedding_model=StubModel(),
            top_k=top_k,
            temporal_weight=0.5,
            semantic_weight=0.5,
            threshold=threshold,
        )

    def test_top_k_respected(self):
        result = self._run_align("hello world", ["a"] * 10, top_k=3)
        assert len(result.slide_candidates) <= 3

    def test_top_k_one(self):
        result = self._run_align("hello world", ["a"] * 5, top_k=1)
        assert len(result.slide_candidates) == 1

    def test_candidates_sorted_descending(self):
        result = self._run_align("hello world", ["a"] * 6, top_k=6)
        scores = [c.combined_score for c in result.slide_candidates]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# 8. NO_CONFIDENT_SLIDE behaviour
# ---------------------------------------------------------------------------

class TestNoConfidentSlide:
    def test_below_threshold_gives_no_slide(self):
        from src.fusion.multimodal_representation import align_segment, NO_SLIDE
        from src.fusion.temporal_alignment import SlideTimingInfo
        from src.audio.asr import TranscriptSegment

        slide_ids = _make_slide_ids(3)
        embeddings = np.zeros((3, 8), dtype=np.float32)  # zero embeddings → zero similarity
        timings = [SlideTimingInfo(sid) for sid in slide_ids]
        seg = TranscriptSegment(1, 100.0, 110.0, "SPEAKER_01", "")

        class ZeroModel:
            def encode(self, texts, **kw):
                return np.zeros((len(texts), 8), dtype=np.float32)
            def get_sentence_embedding_dimension(self):
                return 8

        result = align_segment(
            segment=seg,
            slide_ids=slide_ids,
            slide_timings=timings,
            slide_embeddings=embeddings,
            embedding_model=ZeroModel(),
            top_k=3,
            temporal_weight=0.5,
            semantic_weight=0.5,
            threshold=0.99,  # impossibly high threshold
        )
        assert result.selected_slide == NO_SLIDE

    def test_above_threshold_gives_slide(self):
        from src.fusion.multimodal_representation import align_segment, NO_SLIDE
        from src.fusion.temporal_alignment import SlideTimingInfo
        from src.audio.asr import TranscriptSegment

        slide_ids = ["slide_01"]
        # Identical embeddings → cosine similarity = 1.0
        emb = np.ones((1, 8), dtype=np.float32)
        timings = [SlideTimingInfo("slide_01")]
        seg = TranscriptSegment(1, 0.0, 5.0, "SPEAKER_01", "test text")

        class IdenticalModel:
            def encode(self, texts, **kw):
                return np.ones((len(texts), 8), dtype=np.float32)
            def get_sentence_embedding_dimension(self):
                return 8

        result = align_segment(
            segment=seg,
            slide_ids=slide_ids,
            slide_timings=timings,
            slide_embeddings=emb,
            embedding_model=IdenticalModel(),
            top_k=1,
            temporal_weight=0.0,
            semantic_weight=1.0,
            threshold=0.5,
        )
        assert result.selected_slide == "slide_01"


# ---------------------------------------------------------------------------
# 9. Multimodal representation creation
# ---------------------------------------------------------------------------

class TestMultimodalRepresentation:
    def test_structure(self):
        from src.fusion.multimodal_representation import (
            MultimodalSegment, AlignmentResult, SlideCandidate
        )
        candidate = SlideCandidate(
            slide_id="slide_01",
            temporal_score=0.8,
            semantic_score=0.7,
            combined_score=0.75,
            confidence="high",
        )
        ar = AlignmentResult(
            segment_id=5,
            speaker="SPEAKER_02",
            start=100.0,
            end=110.0,
            text="Sample text",
            slide_candidates=[candidate],
            selected_slide="slide_01",
        )
        mm = MultimodalSegment(
            segment_id=ar.segment_id,
            speaker=ar.speaker,
            start=ar.start,
            end=ar.end,
            text=ar.text,
            slide_id=ar.selected_slide,
            temporal_score=candidate.temporal_score,
            semantic_score=candidate.semantic_score,
            combined_score=candidate.combined_score,
        )
        assert mm.slide_id == "slide_01"
        assert mm.temporal_score == pytest.approx(0.8)
        assert mm.combined_score == pytest.approx(0.75)

    def test_no_slide_multimodal(self):
        from src.fusion.multimodal_representation import MultimodalSegment, NO_SLIDE
        mm = MultimodalSegment(
            segment_id=1,
            speaker="SPEAKER_01",
            start=0.0,
            end=5.0,
            text="",
            slide_id=NO_SLIDE,
            temporal_score=None,
            semantic_score=None,
            combined_score=None,
        )
        assert mm.slide_id == NO_SLIDE
        assert mm.temporal_score is None


# ---------------------------------------------------------------------------
# 10. Invalid input handling
# ---------------------------------------------------------------------------

class TestInvalidInputs:
    def test_missing_transcript(self, tmp_path):
        from src.fusion.multimodal_representation import run_alignment
        with pytest.raises(FileNotFoundError, match="Transcript JSON not found"):
            run_alignment(
                transcript_path=tmp_path / "missing_transcript.json",
                slides_path=tmp_path / "slides.json",
            )

    def test_missing_slides(self, tmp_path):
        from src.fusion.multimodal_representation import run_alignment
        # Create a dummy transcript file
        t = tmp_path / "transcript.json"
        t.write_text("{}", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Slides JSON not found"):
            run_alignment(
                transcript_path=t,
                slides_path=tmp_path / "missing_slides.json",
            )

    def test_missing_embeddings(self, tmp_path):
        from src.fusion.multimodal_representation import run_alignment
        t = tmp_path / "transcript.json"
        t.write_text("{}", encoding="utf-8")
        s = tmp_path / "slides.json"
        s.write_text("{}", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Slide embeddings not found"):
            run_alignment(
                transcript_path=t,
                slides_path=s,
                embeddings_path=tmp_path / "missing.npy",
            )

    def test_semantic_scores_dim_mismatch(self):
        from src.fusion.semantic_alignment import compute_semantic_scores

        class DummyModel:
            def encode(self, texts, **kw):
                return np.ones((len(texts), 4), dtype=np.float32)
            def get_sentence_embedding_dimension(self):
                return 4

        # 3 slide_ids but only 2 rows in embeddings → should raise ValueError
        with pytest.raises(ValueError, match="does not match"):
            compute_semantic_scores(
                "some text",
                ["slide_01", "slide_02", "slide_03"],
                np.ones((2, 4), dtype=np.float32),
                DummyModel(),
            )


# ---------------------------------------------------------------------------
# 11. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def _stub_align(self, seg_text, n_slides, threshold=0.0):
        from src.fusion.multimodal_representation import align_segment
        from src.fusion.temporal_alignment import SlideTimingInfo
        from src.audio.asr import TranscriptSegment

        slide_ids = _make_slide_ids(n_slides)
        embeddings = _make_random_embeddings(n_slides)
        timings = [SlideTimingInfo(sid) for sid in slide_ids]

        class RandModel:
            def encode(self, texts, **kw):
                rng = np.random.default_rng(len(texts[0]) if texts[0] else 0)
                return rng.random((len(texts), 8)).astype(np.float32)
            def get_sentence_embedding_dimension(self): return 8

        seg = TranscriptSegment(1, 0.0, 5.0, "SPEAKER_01", seg_text)
        return align_segment(
            segment=seg, slide_ids=slide_ids, slide_timings=timings,
            slide_embeddings=embeddings, embedding_model=RandModel(),
            top_k=3, temporal_weight=0.5, semantic_weight=0.5, threshold=threshold,
        )

    def test_empty_segment_text(self):
        result = self._stub_align("", n_slides=5, threshold=0.0)
        # Should not raise; may or may not find a slide
        assert result.segment_id == 1

    def test_single_slide(self):
        result = self._stub_align("test", n_slides=1, threshold=0.0)
        assert len(result.slide_candidates) == 1

    def test_many_slides(self):
        result = self._stub_align("test", n_slides=50, threshold=0.0)
        assert len(result.slide_candidates) <= 3

    def test_timing_info_from_dict(self):
        from src.fusion.temporal_alignment import timing_from_slide_dict
        d = {"slide_id": "slide_03", "start_time": 60.0, "end_time": 90.0}
        t = timing_from_slide_dict(d)
        assert t.slide_id == "slide_03"
        assert t.start_time == 60.0
        assert t.has_timing is True

    def test_timing_info_missing_keys(self):
        from src.fusion.temporal_alignment import timing_from_slide_dict
        d = {"slide_id": "slide_03"}
        t = timing_from_slide_dict(d)
        assert t.has_timing is False

    def test_empty_slide_text_embed(self):
        from src.fusion.semantic_alignment import embed_text

        class DummyModel:
            def encode(self, texts, **kw):
                return np.ones((len(texts), 4), dtype=np.float32)
            def get_sentence_embedding_dimension(self):
                return 4

        emb = embed_text("", DummyModel())
        assert emb.shape == (4,)
        assert np.all(emb == 0.0)


# ---------------------------------------------------------------------------
# 12. JSON serialisation of alignment results
# ---------------------------------------------------------------------------

class TestAlignmentSerialisation:
    def test_alignment_to_dict(self):
        from src.fusion.multimodal_representation import (
            AlignmentResult, SlideCandidate, _alignment_to_dict
        )
        ar = AlignmentResult(
            segment_id=1,
            speaker="SPEAKER_01",
            start=0.0, end=5.0,
            text="hello",
            slide_candidates=[
                SlideCandidate("slide_01", 0.9, 0.8, 0.85, "high")
            ],
            selected_slide="slide_01",
        )
        d = _alignment_to_dict(ar)
        assert d["segment_id"] == 1
        assert d["selected_slide"] == "slide_01"
        assert d["slide_candidates"][0]["slide_id"] == "slide_01"
        # Round-trip JSON
        json.dumps(d)  # must not raise

    def test_multimodal_to_dict(self):
        from src.fusion.multimodal_representation import (
            MultimodalSegment, _multimodal_to_dict
        )
        mm = MultimodalSegment(
            segment_id=2, speaker="SPEAKER_02",
            start=10.0, end=20.0, text="something",
            slide_id="slide_03",
            temporal_score=0.6, semantic_score=0.7, combined_score=0.65,
        )
        d = _multimodal_to_dict(mm)
        assert d["slide_id"] == "slide_03"
        assert d["alignment"]["temporal_score"] == pytest.approx(0.6)
        json.dumps(d)  # must not raise
