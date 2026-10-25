import json

import numpy as np
import pytest
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from scripts.improve_decision_discussions import context_texts, smooth_scores
from src.meeting import discussions


def test_batched_runtime_scores_match_reference_features_and_smoothing():
    rows = [{'meeting': m, 'start': t, 'end': t+1, 'act_id': str(i), 'text': text}
            for i, (m, t, text) in enumerate([
                ('A', 2, 'green design'), ('B', 0, 'private budget'),
                ('A', 0, 'blue design'), ('A', 4, 'green button')])]
    vectors = {key: TfidfVectorizer().fit([r['text'] for r in rows])
               for key in ['word', 'char', 'context_40']}
    matrix = hstack([vectors['word'].transform([r['text'] for r in rows]),
                     vectors['char'].transform([r['text'] for r in rows]),
                     vectors['context_40'].transform(context_texts(rows, 40))], format='csr')
    model = LogisticRegression().fit(matrix, [1, 0, 0, 1])
    bundle = {'vectorizers': vectors, 'classifiers': {'linear': model, 'forest': model}, 'context_radius': 40}
    parts = discussions.component_scores(rows, bundle, batch_size=1)
    np.testing.assert_allclose(parts['linear'], model.predict_proba(matrix)[:, 1])
    np.testing.assert_allclose(discussions.combine_scores(rows, parts, .25, 15),
                               smooth_scores(rows, parts['linear'], 15))
    changed = [dict(row, label=1, positive_word_fraction=1) for row in rows]
    np.testing.assert_allclose(discussions.component_scores(changed, bundle)['linear'], parts['linear'])


def test_review_retains_verbatim_source_and_never_creates_decision_events(tmp_path, monkeypatch):
    path = tmp_path/'model.joblib'; path.write_bytes(b'fixture')
    bundle = {'linear_weight': .25, 'smoothing_radius': 0, 'threshold': .5,
              'method': 'test_review', 'selection_sha256': 'frozen'}
    monkeypatch.setattr(discussions, '_load_model', lambda *args: bundle)
    monkeypatch.setattr(discussions, 'component_scores', lambda rows, model:
                        {'linear': np.array([.9, .1]), 'forest': np.array([.8, .2])})
    segments = [{'segment_id': 7, 'start': 1., 'end': 2., 'speaker': 'A', 'text': '<source> We could choose green.'},
                {'segment_id': 8, 'start': 3., 'end': 4., 'speaker': 'B', 'text': 'Other speech'}]
    result = discussions.review_discussions(segments, 'm', 'en', path)
    assert result['status'] == 'ready' and len(result['passages']) == 1
    passage = result['passages'][0]
    assert passage['source_segment_id'] == 7 and passage['text'] == segments[0]['text']
    assert passage['speaker'] == 'A' and passage['start'] == 1.
    assert 'event_type' not in passage and result['accuracy_measured'] is False
    assert discussions.review_discussions(segments, 'm', 'hi', path)['status'] == 'unsupported_language'
    assert discussions.review_discussions(segments, 'm', 'en', tmp_path/'missing')['status'] == 'model_unavailable'
    for invalid in [dict(segments[0], start=float('nan')), dict(segments[0], end=-1),
                    dict(segments[0], text=None), dict(segments[0], segment_id=True)]:
        with pytest.raises(ValueError):
            discussions.review_discussions([invalid], 'm', 'en', path)
    with pytest.raises(ValueError):
        discussions.review_discussions([segments[0], segments[0]], 'm', 'en', path)


def test_optional_stage_failure_is_explicit_and_does_not_break_rule_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(discussions, 'get', lambda key, default=None: default)
    monkeypatch.setattr(discussions, 'review_discussions', lambda *args: (_ for _ in ()).throw(ValueError('invalid model')))
    result = discussions.run_discussion_review([], 'm', 'en', tmp_path)
    assert result['status'] == 'error' and result['passages'] == []
    assert json.loads((tmp_path/'discussions/m_discussions.json').read_text())['status'] == 'error'


@pytest.mark.parametrize('research_options', [False, 'roles', 'ranking'])
def test_learned_stage_reaches_complete_pipeline_and_all_report_formats(tmp_path, monkeypatch, research_options):
    from src.pipeline import orchestrator
    from src.audio.asr import TranscriptResult, TranscriptSegment
    from dataclasses import asdict
    import src.audio.asr
    import src.audio.preprocess

    segments = [TranscriptSegment(1, 0., 2., 'UNKNOWN', '<source> We could choose green.'),
                TranscriptSegment(2, 3., 4., 'UNKNOWN', 'Other speech')]
    transcript = TranscriptResult('m', 'en', 5., 0, [], segments, detected_languages=['en'])
    path = tmp_path/'data/processed/audio/m_transcript.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(asdict(transcript)))
    monkeypatch.setattr(orchestrator, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(orchestrator, 'save_resume_state', lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, 'mark_stage_complete', lambda *args, **kwargs: None)
    monkeypatch.setattr(src.audio.preprocess, 'preprocess_audio', lambda *args, **kwargs: (tmp_path/'audio.wav', {}))
    monkeypatch.setattr(src.audio.asr, 'run_asr', lambda *args, **kwargs: (transcript, path, {}))
    seen = []

    def review(rows, meeting, language, model):
        seen.append((meeting, language, rows))
        return {'status': 'ready', 'passages': [{'source_segment_id': 1, 'start': 0., 'end': 2.,
            'speaker': 'UNKNOWN', 'text': segments[0].text, 'score': .8}], 'requires_review': True}

    monkeypatch.setattr(discussions, 'review_discussions', review)
    options = {}
    if research_options:
        from src.meeting.events import KeywordEventExtractor
        monkeypatch.setattr('src.meeting.learned_events.ContextualRoleExtractor', lambda directory: KeywordEventExtractor())
        monkeypatch.setattr('src.meeting.topics.infer_event_topics', lambda events, *args: {event.event_id: 0 for event in events})
        monkeypatch.setattr('src.meeting.ranking.rank_participants', lambda *args:
                            {'status': 'experimental_outcome_alignment_ranking', 'participants': [], 'accuracy_measured': False})
        options = {'discussion_model': 'mock', 'topic_aware': True, 'outcome_links': True}
        options['event_model' if research_options == 'roles' else 'ranker_model'] = 'mock'
    report_path = orchestrator.run_meeting(tmp_path/'audio.wav', 'm', diarization='off', options=options)
    data = json.loads(report_path.read_text())
    assert seen[0][:2] == ('m', 'en') and seen[0][2][0]['segment_id'] == 1
    assert data['processing']['discussion_review_status'] == 'ready'
    assert data['discussion_review']['passages'][0]['text'] == segments[0].text
    assert data['processing']['accuracy_measured'] is False
    if research_options:
        assert data['outcome_links']['status'] == 'independent_annotations_required'
        assert (tmp_path/'data/processed/outcomes/m_outcomes.json').exists()
        if research_options == 'roles':
            assert 'Contextual English contributions' in data['processing']['analysis_method']
        else:
            assert data['experimental_ranking']['accuracy_measured'] is False
    html = report_path.with_suffix('.html').read_text()
    markdown = report_path.with_suffix('.md').read_text()
    assert '&lt;source&gt;' in html and '<source>' not in html
    assert 'Discussion passages to review' in markdown and segments[0].text in markdown
    from src.report.transcript_export import render_export
    for format in ['md', 'txt']:
        download, _ = render_export(data, 'Meeting', format)
        assert 'Discussion passages to review' in download
        assert 'source segment 1' in download and segments[0].text in download


def test_imported_discussion_suggestions_must_match_real_transcript_sources():
    from src.report.portable import website_report
    segment = {'segment_id': 1, 'speaker': 'A', 'text': 'Exact source', 'start': 0., 'end': 1.}
    passage = {'source_segment_id': 1, 'speaker': 'A', 'text': 'Exact source', 'start': 0., 'end': 1.}
    source = {'completed': True, 'duration': 2., 'transcript_segments': [segment],
              'discussion_review': {'status': 'ready', 'passages': [passage]}}
    assert website_report(source)['discussion_review']['passages'][0]['text'] == 'Exact source'
    for bad in [None, {'passages': None}, {'passages': ['bad']},
                {'passages': [dict(passage, text='Invented text')]},
                {'passages': [dict(passage, source_segment_id=99)]}]:
        with pytest.raises(ValueError):
            website_report(dict(source, discussion_review=bad))
