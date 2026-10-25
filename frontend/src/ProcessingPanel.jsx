import { useEffect, useState } from 'react';
import { Activity, CheckCircle2, Clock3, ShieldCheck } from 'lucide-react';

const stageLabels = { queued: 'Waiting for the local processor', decoding: 'Preparing audio', preprocessing: 'Checking audio', transcription: 'Transcribing audio', diarization: 'Separating speakers', attribution: 'Assigning words to speakers', slides: 'Reading presentation', alignment: 'Matching discussion to slides', events: 'Extracting NLP events', decisions: 'Reconstructing decisions', interactions: 'Analysing interactions', influence: 'Calculating influence', report: 'Saving results' };
const time = seconds => {
  const value = Math.max(0, Math.floor(seconds || 0));
  return `${Math.floor(value / 3600) ? `${Math.floor(value / 3600)}:` : ''}${String(Math.floor(value / 60) % 60).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
};

export default function ProcessingPanel({ status, stage, progress, preview, connectionError }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const sinceUpdate = Math.max(0, (now - (progress?.received_at || now)) / 1000);
  const elapsed = (progress?.elapsed_seconds || 0) + (status === 'processing' ? sinceUpdate : 0);
  const stageElapsed = (progress?.stage_elapsed_seconds || 0) + (status === 'processing' ? sinceUpdate : 0);
  const percent = progress?.overall_percent;
  const stagePercent = progress?.stage_percent ?? (progress?.total_seconds > 0 ? progress.completed_seconds / progress.total_seconds * 100 : null);
  const remaining = progress?.estimated_remaining_seconds;
  const stages = progress?.stages || ['transcription', 'diarization', 'attribution', 'slides', 'alignment', 'events', 'decisions', 'interactions', 'influence', 'report'];
  return <section className="panel stack processing-panel" aria-label="Meeting processing">
    <div className="section-heading"><div className="processing-title"><span className="live-icon"><Activity aria-hidden="true" /></span><div><p className="eyebrow">{status === 'queued' ? 'Queued' : status === 'loading' ? 'Opening meeting' : 'Processing locally'}</p><h2 role="status">{status === 'loading' ? 'Loading meeting progress' : stageLabels[stage] || 'Preparing your meeting'}</h2></div></div><span className="privacy-badge"><ShieldCheck aria-hidden="true" /> Local &amp; private</span></div>
    <div className="processing-metrics"><div><span><Clock3 aria-hidden="true" /> Processing elapsed</span><strong>{time(elapsed)}</strong></div><div><span>Estimated remaining</span><strong>{remaining != null ? remaining > sinceUpdate ? `~${time(remaining - sinceUpdate)}` : 'Updating…' : 'Calculating…'}</strong></div><div><span>Overall stage estimate</span><strong>{percent != null ? `${Math.floor(percent)}%` : 'In progress'}</strong></div></div>
    <div><progress aria-label="Overall processing progress" max="100" {...(percent != null ? { value: percent } : {})} /><p className="small muted">{remaining != null && remaining > sinceUpdate ? `Estimated finish ${new Date(now + (remaining - sinceUpdate) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}. ` : ''}Overall percentage and finish time are estimates. The stage counter below measures audio processed.</p></div>
    {status === 'processing' && <div className="stage-progress"><div className="section-heading"><strong>{stageLabels[stage]}</strong><span className="small">{stagePercent != null ? `${Math.floor(stagePercent)}% · ` : ''}{time(stageElapsed)} in this stage</span></div>{stagePercent != null ? <><progress aria-label="Current stage progress" max="100" value={stagePercent} /><p className="small muted">{time(progress.completed_seconds)} / {time(progress.total_seconds)} of audio {stage === 'diarization' ? 'examined for speakers' : stage === 'attribution' ? 'attributed' : 'processed'}{progress.cached ? ' · using saved results' : ''}{progress?.phase === 'clustering' ? ' · final speaker clustering' : ''}</p></> : <p className="small muted">This step has no measured counter yet. Elapsed time continues updating.</p>}{progress?.remaining_stage_seconds > 0 && remaining == null && <p className="small muted">About {time(Math.max(0, progress.remaining_stage_seconds - sinceUpdate))} left in this stage. Total finish time needs timings from a comparable local run.</p>}</div>}
    <ol className="stage-list" aria-label="Analysis stages">{stages.map(name => <li key={name} className={name === stage ? 'active' : name in (progress?.stage_timings_seconds || {}) ? 'done' : ''}>{name in (progress?.stage_timings_seconds || {}) ? <CheckCircle2 aria-hidden="true" /> : <span className="stage-dot" />}<span>{stageLabels[name]}</span></li>)}</ol>
    {stage === 'decoding' && progress?.parts_total > 0 && <p className="small muted">{progress.parts_completed} of {progress.parts_total} audio files prepared, in upload order.</p>}
    {connectionError && <p role="status" className="notice error">Connection interrupted. Reconnecting automatically; local processing continues.</p>}
    <p className="small muted">Results appear here automatically. Draft text is saved after each audio chunk; speaker assignments and influence are finalised after the full recording is analysed.</p>
    {!!preview?.transcript_segments?.length && <details open><summary>Transcript so far — from the beginning · draft · {preview.total_segments || preview.transcript_segments.length} passages saved</summary><div className="draft-transcript">{preview.transcript_segments.map(s => <p key={s.segment_id} className="preview-text"><span className="small muted">{time(s.start)} </span>{s.text}</p>)}</div></details>}
  </section>;
}
