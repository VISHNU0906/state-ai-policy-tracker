import pytest
from pipeline import dedupe, enrich, llm

@pytest.mark.parametrize('verb', ['cancels', 'scraps', 'revokes', 'withdraws', 'suspends', 'halts'])
def test_reversal_is_a_separate_event_even_for_reused_url(verb):
    rows=[dict(state='Odisha', date='2026-05-01', title='Odisha approves AI university contract', url='https://example.org/story'),
          dict(state='Odisha', date='2026-05-02', title=f'Odisha {verb} AI university contract', url='https://example.org/story')]
    assert len(dedupe.cluster(rows)) == 2
    for row in rows: row.pop('url')
    assert len(dedupe.cluster(rows)) == 2

def test_shared_url_does_not_join_different_states():
    rows=[dict(state=s, date='2026-05-01', title='Government approves AI university', url='https://example.org/story') for s in ['Odisha','Assam']]
    assert len(dedupe.cluster(rows)) == 2

def test_offline_missing_cache_is_explicit_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(enrich, 'CACHE', tmp_path)
    monkeypatch.setenv('PIPELINE_OFFLINE','1')
    def forbidden(*a, **kw): raise AssertionError('Network access attempted')
    monkeypatch.setattr(enrich.requests,'get', forbidden)
    result = enrich.enrich({'url':'https://example.org/uncached'})
    assert result['fetch_status'] == 'offline_cache_miss'
    assert not list(tmp_path.iterdir())

def test_offline_disables_optional_model_calls(monkeypatch):
    monkeypatch.setenv('PIPELINE_OFFLINE','1')
    monkeypatch.setenv('ANTHROPIC_API_KEY','test-not-a-key')
    records=[{'record_id':'example'}]
    assert llm.refine(records) is records
