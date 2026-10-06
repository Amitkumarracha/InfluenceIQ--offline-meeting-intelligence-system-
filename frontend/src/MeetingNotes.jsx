import { useState } from 'react';
import axios from 'axios';

export default function MeetingNotes({ api, id, data, models, status, progress, error, onQueued, seek }) {
  const [model, setModel] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const selectedModel = model || models[0] || '';
  const generating = ['queued', 'processing'].includes(status);
  const sources = item => <button className="text-indigo-700 underline text-sm mt-2" onClick={() => seek(item.start)}>
    Listen at {Math.floor(item.start / 60)}:{String(Math.floor(item.start % 60)).padStart(2, '0')} · “{item.quote}”
  </button>;
  const generate = async () => {
    setMessage(''); setBusy(true);
    try { await axios.post(`${api}/meetings/${id}/summarize`, { model: selectedModel }); onQueued(); }
    catch (err) { setMessage(err.response?.data?.detail || 'Could not generate local notes.'); }
    finally { setBusy(false); }
  };
  const ask = async event => {
    event.preventDefault(); setMessage(''); setBusy(true); setAnswer(null);
    try { const res = await axios.post(`${api}/meetings/${id}/ask`, { question, model: selectedModel || null }); setAnswer(res.data); }
    catch (err) { setMessage(err.response?.data?.detail || 'Could not search this meeting.'); }
    finally { setBusy(false); }
  };
  return <section className="bg-white rounded-2xl border border-slate-200 p-6 space-y-5">
    <div className="flex flex-wrap justify-between items-center gap-3">
      <div><h3 className="font-bold text-xl">Meeting notes & questions</h3><p className="text-sm text-slate-500">Local AI drafts with transcript evidence. Review decisions and commitments.</p></div>
      <div className="flex flex-wrap gap-2 print:hidden">
        <select aria-label="Local notes model" value={selectedModel} onChange={e => setModel(e.target.value)} disabled={busy || generating} className="border rounded-lg p-2 max-w-full">
          {!models.length && <option value="">Transcript search only</option>}
          {models.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <button onClick={generate} disabled={!selectedModel || busy || generating} className="bg-indigo-600 disabled:bg-slate-400 text-white rounded-lg px-4 py-2">{generating ? 'Generating notes…' : data.local_notes ? 'Regenerate notes' : 'Generate notes'}</button>
      </div>
    </div>
    {!models.length && <p className="text-sm text-slate-600 print:hidden">Local AI is not ready. Start Ollama with a downloaded local model, then refresh the app. Transcript search and exports work now.</p>}
    {generating && <p role="status" className="bg-indigo-50 rounded-lg p-3">{status === 'queued' ? 'Notes queued behind current processing.' : `Notes: ${progress?.completed_chunks || 0} / ${progress?.total_chunks || '…'} transcript parts processed.`} Completed parts are saved for recovery.</p>}
    {(message || error) && <p role="alert" className="text-red-700">{message || error}</p>}
    {data.local_notes && <>
      <p className="text-xs text-slate-500">{data.local_notes.model} · {data.local_notes.chunks} parts · {data.local_notes.rejected_items} unsupported items omitted. Quotes were checked; interpretation still needs review.</p>
      {[['overview', 'Overview'], ['decisions', 'Decision candidates'], ['action_items', 'Action candidates'], ['open_questions', 'Open questions']].map(([key, title]) => <div key={key}>
        <h4 className="font-bold mb-2">{title}</h4>
        {data.local_notes[key]?.length ? <ul className="space-y-3">{data.local_notes[key].map((item, i) => <li key={i} className="bg-slate-50 p-3 rounded-lg">
          <p>{item.text}</p>{key === 'action_items' && <p className="text-xs text-slate-500 mt-1">Owner: {item.owner || 'Not stated'} · Due: {item.due || 'Not stated'}</p>}{sources(item)}
        </li>)}</ul> : <p className="text-sm text-slate-500">No cited candidates returned.</p>}
      </div>)}
    </>}
    <form onSubmit={ask} className="flex flex-wrap gap-2 print:hidden">
      <input aria-label="Question about this meeting" value={question} onChange={e => setQuestion(e.target.value)} required maxLength={500} placeholder="Ask about a decision, name or topic…" className="flex-1 min-w-0 border rounded-lg p-3" />
      <button disabled={busy || generating || !question.trim()} className="bg-slate-800 disabled:bg-slate-400 text-white rounded-lg px-4 py-2">{busy ? 'Working…' : selectedModel ? 'Ask meeting' : 'Find passages'}</button>
    </form>
    {answer && <div className="space-y-3"><p className="text-sm text-slate-500">{answer.message}</p>
      {answer.answers?.map((item, i) => <div key={i} className="bg-indigo-50 p-3 rounded-lg"><p>{item.text}</p>{sources(item)}</div>)}
      <details><summary className="cursor-pointer font-medium">Retrieved passages ({answer.sources?.length || 0})</summary>
        {answer.sources?.map(hit => <div key={hit.segment_id} className="p-3 border-b"><button onClick={() => seek(hit.start)} className="text-indigo-700 underline">Listen to passage</button><p>{hit.context.map(s => s.text).join(' ')}</p></div>)}
      </details>
    </div>}
  </section>;
}
