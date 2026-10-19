import React, { useState } from 'react';

export default function TaskReview({ task, review, onSave }) {
  const [editing, setEditing] = useState(false);
  const [owner, setOwner] = useState('');
  const [due, setDue] = useState('');
  const [state, setState] = useState('open');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = review?.human_reviewed === true && review.source_text === task.text && review.source_start === task.timestamp ? review : null;
  const open = () => {
    setOwner(active?.owner || ''); setDue(active?.due_date || ''); setState(active?.state || 'open'); setError(''); setEditing(true);
  };
  const save = async event => {
    event.preventDefault(); setBusy(true); setError('');
    try { await onSave(task.event_id, { owner, due_date: due, state }); setEditing(false); }
    catch (failure) { setError(typeof failure.response?.data?.detail === 'string' ? failure.response.data.detail : 'Could not save this follow-up. Reload the meeting and try again.'); }
    finally { setBusy(false); }
  };
  if (!task.event_id) return <p className="small muted">Reanalyse this historical recording to enable follow-up tracking.</p>;
  return <div className="stack">
    <p className="small muted">{active ? `Reviewed · ${active.state} · Owner: ${active.owner || 'Unassigned'} · Due: ${active.due_date || 'Not set'}` : 'Unreviewed candidate · owner and due date are not assigned.'}</p>
    {!editing ? <button className="print:hidden" onClick={open}>{active ? 'Edit follow-up' : 'Review follow-up'}</button> : <form className="stack print:hidden" aria-label="Review follow-up" onSubmit={save}>
      <p className="small muted">Confirm this task against its recording. Names and dates are your corrections; the speaker is not automatically the owner.</p>
      <label className="stack">Task owner<input aria-label="Task owner" maxLength={100} value={owner} onChange={e => setOwner(e.target.value)} placeholder="Leave blank if unassigned" /></label>
      <label className="stack">Due date<input aria-label="Task due date" type="date" max="9998-12-31" value={due} onChange={e => setDue(e.target.value)} /></label>
      <label className="stack">Task status<select aria-label="Task status" value={state} onChange={e => setState(e.target.value)}><option value="open">Open</option><option value="done">Done</option><option value="dismissed">Dismissed candidate</option></select></label>
      {error && <p role="alert">{error}</p>}
      <div className="button-row"><button className="primary" disabled={busy} type="submit">{busy ? 'Saving…' : 'Save follow-up'}</button><button type="button" disabled={busy} onClick={() => setEditing(false)}>Cancel</button></div>
    </form>}
  </div>;
}
