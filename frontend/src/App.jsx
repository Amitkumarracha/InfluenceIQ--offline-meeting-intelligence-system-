import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { flushSync } from 'react-dom';
import { saveChunk, clearRecording, recordingExists, restoreRecording } from './recordingStore';
import MeetingNotes from './MeetingNotes';
import {
  FileAudio, FileVideo, Users, CheckCircle, ChevronRight,
  BarChart3, History, RefreshCw, X, Lock, Mail, MessageSquare,
  Search, Download, Kanban, Edit2, Check,
  Printer, AlignLeft, User, PlayCircle, Mic2
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '/api';

// Add global interceptor for JWT
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [email, setEmail] = useState(localStorage.getItem('userEmail') || '');

  // Local accounts do not send email or reset links.
  const [authView, setAuthView] = useState('login');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authSuccess, setAuthSuccess] = useState('');

  const [meetings, setMeetings] = useState([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [transcriptSearch, setTranscriptSearch] = useState('');
  const [preview, setPreview] = useState(null);

  const [audioFiles, setAudioFiles] = useState(null);
  const [pptFiles, setPptFiles] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [meetingTitle, setMeetingTitle] = useState('');
  const [speechModel, setSpeechModel] = useState('');
  const [speechModels, setSpeechModels] = useState([]);
  const [language, setLanguage] = useState('auto');
  const [vocabulary, setVocabulary] = useState('');
  const [diarization, setDiarization] = useState('auto');
  const [numSpeakers, setNumSpeakers] = useState('');
  const [summaryModels, setSummaryModels] = useState([]);
  const [summaryStatus, setSummaryStatus] = useState(null);
  const [summaryProgress, setSummaryProgress] = useState(null);
  const [summaryError, setSummaryError] = useState(null);
  const [jobProgress, setJobProgress] = useState(null);
  const [exportFormat, setExportFormat] = useState('json');
  const [libraryHits, setLibraryHits] = useState(null);
  const [transcriptPage, setTranscriptPage] = useState(0);
  const [printing, setPrinting] = useState(false);
  const audioRef = React.useRef(null);
  const selectedRef = React.useRef(null);

  const [reportData, setReportData] = useState(null);
  const [meetingStatus, setMeetingStatus] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [reportViewTab, setReportViewTab] = useState('highlights'); // 'highlights' or 'transcript'

  const [speakerNames, setSpeakerNames] = useState({});
  const [editingSpeaker, setEditingSpeaker] = useState(null);
  const [editNameValue, setEditNameValue] = useState('');

  // --- Recording State ---
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [captureSource, setCaptureSource] = useState('mic');
  const [devices, setDevices] = useState([]);
  const [deviceId, setDeviceId] = useState('');
  const recordingResources = React.useRef(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = React.useRef(null);
  const recordingWriteRef = React.useRef(Promise.resolve());
  const [hasDraft, setHasDraft] = useState(null);
  const [processingStage, setProcessingStage] = useState(null);
  const [modelReady, setModelReady] = useState(null);
  const timerRef = React.useRef(null);

  // --- Authentication Handlers ---
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError(''); setAuthSuccess('');
    try {
      if (authView === 'login') {
        const res = await axios.post(`${API_URL}/auth/login`, { email: authEmail, password: authPassword });
        localStorage.setItem('token', res.data.token);
        localStorage.setItem('userEmail', res.data.email);
        setToken(res.data.token);
        setEmail(res.data.email);
      } else if (authView === 'register') {
        const res = await axios.post(`${API_URL}/auth/register`, { email: authEmail, password: authPassword });
        localStorage.setItem('token', res.data.token);
        localStorage.setItem('userEmail', res.data.email);
        setToken(res.data.token);
        setEmail(res.data.email);
      }
    } catch (err) {
      if (err.response?.status === 422) {
        const errors = err.response.data.detail;
        if (Array.isArray(errors)) {
          setAuthError("Validation Error: " + errors.map(e => `${e.loc[1]}: ${e.msg}`).join(', '));
        } else {
          setAuthError("Invalid input format.");
        }
      } else {
        setAuthError(err.response?.data?.detail || "Authentication failed. Server error.");
      }
    }
  };

  const handleLogout = () => {
    if (mediaRecorderRef.current?.state !== 'inactive') mediaRecorderRef.current?.stop();
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
    setToken(null);
    setEmail('');
    selectedRef.current = null;
    setSelectedMeetingId(null); setReportData(null); setMeetingStatus(null); setSummaryStatus(null); setMeetings([]); setLibraryHits(null);
  };

  // --- Data Fetching ---
  const fetchMeetings = async () => {
    const requestToken = localStorage.getItem('token');
    try {
      const res = await axios.get(`${API_URL}/meetings`);
      if (requestToken && requestToken === localStorage.getItem('token')) setMeetings(res.data.meetings);
    } catch (err) {
      if (err.response?.status === 401) handleLogout();
    }
  };

  useEffect(() => {
    if (!token) return;
    Promise.resolve().then(fetchMeetings);
    const interval = setInterval(fetchMeetings, 10000);
    return () => clearInterval(interval);
  }, [token]);

  useEffect(() => {
    let interval = null;
    if (selectedMeetingId && (['queued', 'processing'].includes(meetingStatus) || ['queued', 'processing'].includes(summaryStatus))) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_URL}/meetings/${selectedMeetingId}`);
          if (selectedRef.current !== selectedMeetingId) return;
          setMeetingStatus(res.data.status);
          setProcessingStage(res.data.stage);
          setJobProgress(res.data.progress); setPreview(res.data.preview);
          setSummaryStatus(res.data.summary_status); setSummaryProgress(res.data.summary_progress); setSummaryError(res.data.summary_error);
          if (res.data.status === 'completed') {
            setReportData(res.data.data);
            setAudioUrl(res.data.audio_url);
            if (!['queued', 'processing'].includes(res.data.summary_status)) clearInterval(interval);
            fetchMeetings();
          } else if (res.data.status === 'failed') {
            clearInterval(interval);
            setError(res.data.error || "Meeting processing failed.");
          }
        } catch (err) { console.error(err); }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [selectedMeetingId, meetingStatus, summaryStatus]);

  // --- App Actions ---
  const loadMeeting = async (id) => {
    selectedRef.current = id;
    setSelectedMeetingId(id);
    setError('');
    setReportData(null);
    setPreview(null);
    setAudioUrl(null);
    setReportViewTab('highlights');
    setTranscriptSearch('');
    setTranscriptPage(0); setSummaryStatus(null); setSummaryError(null); setSummaryProgress(null); setJobProgress(null);
    try { setSpeakerNames(JSON.parse(localStorage.getItem(`speakerNames:${email}:${id}`) || '{}')); } catch { setSpeakerNames({}); }
    try {
      const res = await axios.get(`${API_URL}/meetings/${id}`);
      if (selectedRef.current !== id) return;
      setMeetingStatus(res.data.status);
      setProcessingStage(res.data.stage);
      setMeetingTitle(res.data.title); setJobProgress(res.data.progress); setPreview(res.data.preview);
      setSummaryStatus(res.data.summary_status); setSummaryProgress(res.data.summary_progress); setSummaryError(res.data.summary_error);
      if (res.data.data?.speaker_names) setSpeakerNames(res.data.data.speaker_names);
      if (res.data.status === "failed") setError(res.data.error || "Processing failed");
      setAudioUrl(res.data.audio_url);
      if (res.data.status === 'completed') setReportData(res.data.data);
    } catch { if (selectedRef.current === id) setError("Failed to load meeting."); }
  };

  const handleAnalyze = async (overrideAudioFiles = null) => {
    const targetAudio = overrideAudioFiles || audioFiles;
    if (!targetAudio || targetAudio.length === 0) { setError("Audio file required."); return; }
    setError(''); setUploading(true);
    const formData = new FormData();
    formData.append('title', meetingTitle); formData.append('model_size', speechModel);
    formData.append('language', language); formData.append('vocabulary', vocabulary); formData.append('diarization', diarization);
    if (numSpeakers && diarization !== 'off') formData.append('num_speakers', numSpeakers);
    for(let i=0; i<targetAudio.length; i++) { formData.append('audio', targetAudio[i]); }
    if (pptFiles) { for(let i=0; i<pptFiles.length; i++) { formData.append('ppt', pptFiles[i]); } }
    try {
      const res = await axios.post(`${API_URL}/analyze`, formData, { headers: { 'Content-Type': 'multipart/form-data' }});
      fetchMeetings(); loadMeeting(res.data.meeting_id); setAudioFiles(null); setPptFiles(null);
      if (targetAudio[0]?.name.startsWith("meeting-recording")) { await clearRecording(); setHasDraft(false); }
    } catch (err) { const detail = err.response?.data?.detail; setError(typeof detail === 'string' ? detail : 'Upload failed. Check meeting settings; your saved recording is still available.'); } finally { setUploading(false); }
  };

  useEffect(() => {
    recordingExists().then(count => setHasDraft(count > 0)).catch(() => setError('Recording storage is unavailable. You can still upload audio.'));
    axios.get(`${API_URL}/health`).then(res => { setModelReady(res.data.asr_ready); setSpeechModels(res.data.asr_models || []); setSpeechModel(res.data.asr_model || ''); setSummaryModels(res.data.summary_models || []); }).catch(() => setModelReady(false));
    navigator.mediaDevices?.enumerateDevices().then(list => setDevices(list.filter(d => d.kind === 'audioinput'))).catch(() => {});
    return () => {
      clearInterval(timerRef.current);
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== 'inactive') recorder.stop();
      recorder?.stream.getTracks().forEach(track => track.stop());
      cleanupRecording();
    };
  }, []);

  useEffect(() => {
    const warn = event => { if (isRecording) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [isRecording]);

  useEffect(() => {
    const before = () => flushSync(() => setPrinting(true));
    const after = () => setPrinting(false);
    window.addEventListener('beforeprint', before); window.addEventListener('afterprint', after);
    return () => { window.removeEventListener('beforeprint', before); window.removeEventListener('afterprint', after); };
  }, []);

  const recoverDraft = async () => {
    try { const file = await restoreRecording(); if (file) setAudioFiles([file]); }
    catch { setError('Could not recover the saved recording.'); }
  };

  function cleanupRecording() {
    const resources = recordingResources.current;
    recordingResources.current = null;
    if (!resources) return;
    clearInterval(resources.levelTimer);
    resources.streams.forEach(s => s.getTracks().forEach(track => track.stop()));
    resources.context?.close().catch(() => {});
    setAudioLevel(0); setIsPaused(false);
  }

  const startRecording = async () => {
    let stream;
    try {
      if (hasDraft === null) throw new Error('Saved recording storage is not ready. Wait a moment or upload audio.');
      if (hasDraft) { setError('Recover or discard the saved recording before starting another.'); return; }
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('Microphone recording requires HTTPS or localhost.');
      recordingResources.current = { streams: [] };
      const mic = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, deviceId: deviceId ? { exact: deviceId } : undefined, echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
      recordingResources.current.streams.push(mic);
      const context = new AudioContext(); await context.resume();
      recordingResources.current.context = context;
      const destination = context.createMediaStreamDestination();
      context.createMediaStreamSource(mic).connect(destination);
      if (captureSource === 'tab') {
        if (!navigator.mediaDevices.getDisplayMedia) throw new Error('Tab audio capture is unavailable in this browser. Use microphone or upload a recording.');
        const shared = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
        recordingResources.current.streams.push(shared);
        if (!shared.getAudioTracks().length) throw new Error('No shared audio. Choose a browser tab and enable Share tab audio.');
        context.createMediaStreamSource(shared).connect(destination);
        shared.getVideoTracks().forEach(t => t.addEventListener('ended', () => { if (mediaRecorderRef.current?.state !== 'inactive') mediaRecorderRef.current?.stop(); }, { once: true }));
      }
      stream = destination.stream;
      recordingResources.current.streams.push(stream);
      const analyser = context.createAnalyser(); analyser.fftSize = 1024;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Float32Array(analyser.fftSize);
      recordingResources.current.levelTimer = setInterval(() => { analyser.getFloatTimeDomainData(samples); const rms = Math.sqrt(samples.reduce((sum, v) => sum + v * v, 0) / samples.length); setAudioLevel(Math.min(100, Math.round(rms * 500))); }, 250);
      const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, { ...(mimeType ? { mimeType } : {}), audioBitsPerSecond: 128000 });
      mediaRecorderRef.current = recorder;
      await clearRecording();
      recordingWriteRef.current = Promise.resolve();
      recorder.ondataavailable = event => {
        if (!event.data.size) return;
        recordingWriteRef.current = recordingWriteRef.current.then(() => saveChunk(event.data));
        recordingWriteRef.current.catch(() => {
          setError('Recording storage is full or unavailable. Recording stopped; recover the saved portion.');
          if (recorder.state !== 'inactive') recorder.stop();
        });
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        cleanupRecording();
        clearInterval(timerRef.current);
        setIsRecording(false);
        try { await recordingWriteRef.current; } catch { /* Recover the persisted portion below. */ }
        const saved = await recordingExists().catch(() => 0);
        setHasDraft(saved > 0);
        if (saved) await recoverDraft();
        else setError('No audio was saved. Record for a few seconds and check the microphone.');
      };
      recorder.onerror = () => { setError('Microphone recording was interrupted. Recover the saved recording.'); if (recorder.state !== 'inactive') recorder.stop(); cleanupRecording(); clearInterval(timerRef.current); setIsRecording(false); };
      recorder.start(5000);
      setIsRecording(true);
      setRecordingTime(0);
      const started = Date.now();
      timerRef.current = setInterval(() => setRecordingTime(Math.floor((Date.now() - started) / 1000)), 1000);
    } catch (err) {
      stream?.getTracks().forEach(track => track.stop());
      cleanupRecording();
      setError(err.message || 'Microphone access denied or unavailable.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const formatTime = (secs) => {
    secs = Math.max(0, Math.floor(secs));
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return secs >= 3600 ? `${Math.floor(secs / 3600)}:${String(Math.floor(secs / 60) % 60).padStart(2, '0')}:${s}` : `${m}:${s}`;
  };
  const saveSpeakerName = async (speakerId) => {
    const meetingId = selectedMeetingId;
    const updated = { ...speakerNames, [speakerId]: editNameValue };
    try { await axios.post(`${API_URL}/meetings/${meetingId}/edit`, { speaker_names: updated }); if (selectedRef.current === meetingId) { setSpeakerNames(updated); setEditingSpeaker(null); } }
    catch { setError('Could not save the speaker name.'); }
  };

  const seek = seconds => { if (audioRef.current) { audioRef.current.currentTime = seconds; audioRef.current.play().catch(() => {}); } };

  const exportReport = async () => {
    try {
      const response = await axios.get(`${API_URL}/meetings/${selectedMeetingId}/export`, { params: { format: exportFormat }, responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url; link.download = `${selectedMeetingId}_report.${exportFormat}`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { setError('Report export failed.'); }
  };

  const findContext = (textOrTimestamp) => {
    if (!reportData || !reportData.transcript_segments || reportData.transcript_segments.length === 0) return null;

    let index = -1;
    if (typeof textOrTimestamp === 'string' && textOrTimestamp) {
      const target = textOrTimestamp.trim().toLowerCase();
      // Try exact match first, then substring match
      index = reportData.transcript_segments.findIndex(s => s.text.toLowerCase() === target);
      if (index === -1) {
        index = reportData.transcript_segments.findIndex(s => s.text.toLowerCase().includes(target) || target.includes(s.text.toLowerCase()));
      }
    } else if (typeof textOrTimestamp === 'number') {
      let minDiff = Infinity;
      reportData.transcript_segments.forEach((s, i) => {
        const diff = Math.abs(s.start - textOrTimestamp);
        if (diff < minDiff) { minDiff = diff; index = i; }
      });
    }

    if (index === -1) return null;

    const startIdx = Math.max(0, index - 1);
    const endIdx = Math.min(reportData.transcript_segments.length - 1, index + 1);

    return reportData.transcript_segments.slice(startIdx, endIdx + 1).map(s => ({
      ...s,
      isTarget: s === reportData.transcript_segments[index]
    }));
  };

  // --- Render Auth Screens ---
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center font-sans p-4">
        {/* ... Auth code unchanged ... */}
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
          <div className="bg-slate-900 p-10 text-center">
            <Mic2 className="w-14 h-14 text-indigo-400 mx-auto mb-4" />
            <h1 className="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400 tracking-tight">Meet IQ</h1>
            <p className="text-slate-400 mt-2 text-sm font-medium">Offline Meeting Intelligence</p>
          </div>
          <div className="p-8">
            {authError && <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm font-medium rounded-lg border border-red-200">{authError}</div>}
            {authSuccess && <div className="mb-4 p-3 bg-emerald-50 text-emerald-600 text-sm font-medium rounded-lg border border-emerald-200">{authSuccess}</div>}

            <form onSubmit={handleAuthSubmit} className="space-y-5">
              {(
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Work Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
                    <input type="email" required value={authEmail} onChange={e=>setAuthEmail(e.target.value)} className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="you@company.com" />
                  </div>
                </div>
              )}
              {(authView === 'login' || authView === 'register') && (
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
                    <input type="password" required minLength={8} maxLength={64} value={authPassword} onChange={e=>setAuthPassword(e.target.value)} className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="•••••••• (Min 8 chars)" />
                  </div>
                  {authView === 'login' && (
                    <div className="flex justify-end mt-1">
                      <button type="button" onClick={() => setAuthSuccess('Account recovery is available from the laptop terminal. See the README under Local account recovery.')} className="text-xs text-indigo-600 hover:underline">Forgot password?</button>
                    </div>
                  )}
                </div>
              )}
              <button type="submit" className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold py-3 rounded-lg transition shadow-md flex justify-center items-center">
                {authView === 'login' && 'Sign In to Meet IQ'}
                {authView === 'register' && 'Create Account'}
              </button>
              <div className="text-center text-sm text-slate-500 mt-4">
                {authView === 'login' && <p>Don't have an account? <button type="button" onClick={() => setAuthView('register')} className="text-indigo-600 font-bold hover:underline">Register</button></p>}
                {authView === 'register' && <p>Already have an account? <button type="button" onClick={() => setAuthView('login')} className="text-indigo-600 font-bold hover:underline">Sign in</button></p>}
              </div>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // --- Main App ---
  const filteredMeetings = meetings.filter(m => m.title.toLowerCase().includes(searchQuery.toLowerCase()) || m.id.includes(searchQuery));

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans overflow-hidden print:h-auto print:block print:bg-white">
      {/* Dark Premium Sidebar - HIDDEN ON PRINT */}
      <aside className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col h-full shadow-2xl z-10 flex-shrink-0 text-slate-300 print:hidden">
        <div className="p-6 border-b border-slate-800 flex items-center space-x-3">
          <div className="bg-gradient-to-br from-indigo-500 to-purple-600 p-2 rounded-xl shadow-lg">
            <Mic2 className="text-white w-6 h-6" />
          </div>
          <h1 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-indigo-300 to-purple-300 tracking-tight">Meet IQ</h1>
        </div>

        <div className="p-4 flex-1 flex flex-col overflow-hidden">
          <button
            onClick={() => { selectedRef.current = null; setSelectedMeetingId(null); setReportData(null); setMeetingStatus(null); setSummaryStatus(null); setAudioUrl(null); setMeetingTitle(''); setError(''); }}
            className="w-full mb-6 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 px-4 rounded-xl flex items-center justify-center transition shadow-lg"
          >
            + Analyze New Meeting
          </button>

          <div className="relative mb-6">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input type="text" placeholder="Search history..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-9 pr-3 py-2 bg-slate-800 border-none rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none text-slate-200 placeholder-slate-500" />
          </div>
          <button className="text-xs underline mb-3" onClick={async () => {
            try { const res = await axios.get(`${API_URL}/search`, { params: { q: searchQuery } }); setLibraryHits(res.data.results); }
            catch { setError('Enter a phrase to search saved transcripts.'); }
          }} disabled={!searchQuery.trim()}>Search words across transcripts</button>
          {libraryHits && <div className="overflow-y-auto max-h-48 text-sm mb-3">
            <button onClick={() => setLibraryHits(null)} className="underline">Close results</button>
            {!libraryHits.length && <p>No matching transcript passages.</p>}
            {libraryHits.map(hit => <button key={`${hit.meeting_id}:${hit.segment_id}`} onClick={() => loadMeeting(hit.meeting_id)} className="block text-left p-2 border-b border-slate-700 w-full"><strong>{hit.title}</strong><p className="text-xs">{formatTime(hit.start)} · {hit.text}</p></button>)}
          </div>}

          <div className="flex items-center space-x-2 mb-3 text-slate-500 px-1">
            <History className="w-4 h-4" />
            <h2 className="text-xs font-bold uppercase tracking-widest">Meeting Library</h2>
          </div>

          <div className="space-y-2 overflow-y-auto flex-1 pr-1 custom-scrollbar">
            {filteredMeetings.map(m => (
              <div key={m.id} onClick={() => loadMeeting(m.id)} className={`p-3 rounded-xl cursor-pointer border transition ${selectedMeetingId === m.id ? 'bg-indigo-900/50 border-indigo-500/50 shadow-inner' : 'bg-slate-800/30 border-transparent hover:bg-slate-800'}`}>
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-sm truncate pr-2 text-slate-200">{m.title}</span>
                  {m.status === 'completed' && <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />}
                  {['queued', 'processing'].includes(m.status) && <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin flex-shrink-0" />}
                  {m.status === 'failed' && <X className="w-4 h-4 text-red-400 flex-shrink-0" />}
                </div>
                <div className="text-xs text-slate-500 font-mono truncate">{m.id}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer Logout */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex flex-col space-y-3">
          <div className="flex items-center justify-between px-2 pt-2">
            <div className="flex items-center space-x-3 truncate">
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-indigo-400 font-bold flex-shrink-0 border border-slate-700">
                {email.charAt(0).toUpperCase()}
              </div>
              <p className="font-medium text-xs text-slate-300 truncate">{email}</p>
            </div>
            <button onClick={handleLogout} className="text-xs font-bold text-slate-500 hover:text-red-400 transition">Logout</button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 h-full overflow-y-auto p-10 relative bg-slate-50 print:p-0 print:overflow-visible print:bg-white print:block">
        {error && selectedMeetingId && <p role="alert" className="p-4 bg-red-50 text-red-700">{error}</p>}
        {modelReady === false && <p role="status" className="p-4 bg-amber-50 text-amber-900">Speech model is unavailable. Complete model setup on the laptop before analysis.</p>}
        {hasDraft && !isRecording && <div className="p-4 bg-blue-50 flex flex-wrap gap-3 items-center"><span>Recording saved on this device.</span><button onClick={recoverDraft} className="underline">Recover recording</button><button onClick={async () => { if (!window.confirm('Discard the saved recording on this device?')) return; await clearRecording(); setHasDraft(false); setAudioFiles(null); }} className="underline">Discard recording</button></div>}
        {['queued', 'processing'].includes(meetingStatus) && <p role="status" className="p-4 bg-indigo-50">Processing stage: {processingStage || meetingStatus}. You can return to this meeting later.</p>}
        {meetingStatus === 'failed' && <button className="m-4 underline" onClick={async () => { try { await axios.post(`${API_URL}/meetings/${selectedMeetingId}/retry`); setMeetingStatus('queued'); setError(''); } catch (err) { setError(err.response?.data?.detail || 'Retry failed'); } }}>Retry processing</button>}
        {reportData?.processing?.warnings?.map((warning, i) => <p key={i} className="p-4 bg-amber-50 text-amber-900">{warning}</p>)}


        {/* Upload State */}
        {!selectedMeetingId && (
          <div className="max-w-2xl mx-auto bg-white p-10 rounded-2xl shadow-xl border border-slate-100 animate-fade-in mt-10 print:hidden">
            <h2 className="text-3xl font-extrabold mb-2 text-slate-900">Your next meeting</h2>
            <p className="text-slate-500 mb-8 font-medium">Record on your device or upload meeting audio for local analysis.</p>

            <div className="space-y-6">
              <label className="block text-sm font-semibold">Meeting title<input maxLength={200} value={meetingTitle} onChange={e => setMeetingTitle(e.target.value)} placeholder="Weekly planning, client review…" className="mt-2 w-full border rounded-lg p-3" /></label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className="text-sm">Capture source<select disabled={isRecording} value={captureSource} onChange={e => setCaptureSource(e.target.value)} className="block mt-1 w-full border rounded-lg p-2"><option value="mic">Room microphone</option><option value="tab">Microphone + shared tab audio</option></select></label>
                <label className="text-sm">Microphone<select disabled={isRecording} value={deviceId} onChange={e => setDeviceId(e.target.value)} className="block mt-1 w-full border rounded-lg p-2"><option value="">System default</option>{devices.map((d, i) => d.deviceId && <option key={d.deviceId} value={d.deviceId}>{d.label || `Microphone ${i + 1}`}</option>)}</select></label>
              </div>
              <p className="text-xs text-slate-500">For a large room, use a conference microphone close to participants. Tab audio needs a supported browser and “Share tab audio”. Recording stays on this device until you submit it.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Live Record Card */}
                <div className={`border-2 ${isRecording ? 'border-red-400 bg-red-50' : 'border-slate-300 bg-slate-50 hover:border-indigo-300 hover:bg-indigo-50'} rounded-xl p-8 flex flex-col items-center justify-center transition relative`}>
                  {isRecording ? (
                    <>
                      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                        <div className="w-6 h-6 bg-red-500 rounded-full animate-ping absolute"></div>
                        <div className="w-6 h-6 bg-red-600 rounded-full relative z-10"></div>
                      </div>
                      <span className="text-xl font-black text-red-600 mb-2">{formatTime(recordingTime)}</span>
                      <span className="text-xs">{isPaused ? 'Paused · elapsed time' : audioLevel < 2 ? 'Very quiet — check microphone placement' : 'Microphone active'}</span>
                      <meter min="0" max="100" value={audioLevel} aria-label="Audio input level" className="w-full mt-2" />
                      <button className="underline mt-2" onClick={() => { const recorder = mediaRecorderRef.current; if (recorder?.state === 'recording') { recorder.pause(); setIsPaused(true); } else if (recorder?.state === 'paused') { recorder.resume(); setIsPaused(false); } }}>{isPaused ? 'Resume recording' : 'Pause recording'}</button>
                      <button onClick={stopRecording} className="mt-2 px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold shadow-md transition w-full">Stop & Save</button>
                    </>
                  ) : (
                    <>
                      <Mic2 className="w-12 h-12 text-indigo-400 mb-4" />
                      <span className="text-lg font-bold text-slate-700 text-center">Record Live</span>
                      <span className="text-xs text-slate-400 mt-1 text-center font-medium">Capture directly from browser</span>
                      <button onClick={startRecording} className="mt-4 px-6 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-bold shadow-md transition w-full">Start Recording</button>
                    </>
                  )}
                </div>

                {/* File Upload Card */}
                <div className={`border-2 border-dashed ${isRecording ? 'opacity-50 pointer-events-none' : ''} border-slate-300 rounded-xl p-8 flex flex-col items-center justify-center bg-slate-50 hover:bg-indigo-50 hover:border-indigo-300 transition relative group`}>
                  <FileAudio className="w-12 h-12 text-indigo-400 mb-4 group-hover:scale-110 transition duration-300" />
                  <span className="text-lg font-bold text-slate-700 text-center">Upload Audio</span>
                  <span className="text-xs text-slate-400 mt-1 text-center font-medium">Drop .wav, .mp3, .m4a</span>
                  <input type="file" multiple accept="audio/*" onChange={(e) => setAudioFiles(e.target.files)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                  {audioFiles && audioFiles.length > 0 && !isRecording && <div className="mt-4 px-4 py-1.5 bg-indigo-600 text-white rounded-full text-xs font-bold shadow-md text-center">{audioFiles.length} file(s) ready</div>}
                </div>
              </div>

              {/* PPT Upload - Optional */}
              <div className={`border-2 border-dashed border-slate-300 rounded-xl p-6 flex flex-col items-center justify-center bg-slate-50 hover:bg-indigo-50 hover:border-indigo-300 transition relative group ${isRecording ? 'opacity-50 pointer-events-none' : ''}`}>
                <FileVideo className="w-8 h-8 text-indigo-300 mb-2 group-hover:scale-110 transition duration-300" />
                <span className="text-sm font-bold text-slate-600">Add Boardroom Presentation (.pptx) (Optional)</span>
                <input aria-label="Optional presentation" type="file" accept=".pptx" onChange={(e) => setPptFiles(e.target.files)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                {pptFiles && pptFiles.length > 0 && <p className="mt-2 text-xs text-indigo-600 font-bold bg-indigo-100 px-3 py-1 rounded-full">{pptFiles.length} file(s) selected</p>}
              </div>
              {audioFiles?.length > 0 && <ol className="text-sm space-y-2">{Array.from(audioFiles).map((file, i) => <li key={`${file.name}:${i}`} className="flex items-center gap-2"><span className="flex-1 min-w-0 break-words">Part {i + 1}: {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)</span><button disabled={i === 0 || uploading} onClick={() => { const parts = Array.from(audioFiles); [parts[i - 1], parts[i]] = [parts[i], parts[i - 1]]; setAudioFiles(parts); }} className="underline">Move up</button><button disabled={uploading} onClick={() => setAudioFiles(Array.from(audioFiles).filter((_, j) => j !== i))} className="underline">Remove</button></li>)}</ol>}
              <details className="border rounded-lg p-4"><summary className="cursor-pointer font-semibold">Transcription settings</summary>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4 text-sm">
                  <label>Speech model<select aria-label="Speech model" value={speechModel} onChange={e => setSpeechModel(e.target.value)} className="block w-full border rounded p-2">{!speechModels.length && <option value={speechModel}>{speechModel || 'No installed model'}</option>}{speechModels.map(m => <option key={m} value={m}>{m}</option>)}</select></label>
                  <label>Language<select aria-label="Language" value={language} onChange={e => setLanguage(e.target.value)} className="block w-full border rounded p-2"><option value="auto">Hindi / English automatic</option><option value="en">English</option><option value="hi">Hindi</option></select></label>
                  <label>Speaker separation<select aria-label="Speaker separation" value={diarization} onChange={e => setDiarization(e.target.value)} className="block w-full border rounded p-2"><option value="auto">Try available local model</option><option value="required">Require speaker model</option><option value="off">Off</option></select></label>
                  <label>Expected speakers (optional)<input type="number" min={1} max={50} value={numSpeakers} disabled={diarization === 'off'} onChange={e => setNumSpeakers(e.target.value)} className="block w-full border rounded p-2" /></label>
                </div>
                <label className="block text-sm mt-3">Names and technical vocabulary<textarea maxLength={1000} value={vocabulary} onChange={e => setVocabulary(e.target.value)} placeholder="Names, acronyms and unusual spellings heard in this meeting" className="block w-full border rounded p-2 mt-1" /></label>
                <p className="text-xs text-slate-500 mt-2">Larger models need more time and memory. Vocabulary provides spelling hints; it does not guarantee recognition. Sequential audio parts are joined in the displayed order.</p>
              </details>
            </div>

            {error && <p className="text-red-500 text-sm mt-6 text-center font-bold bg-red-50 py-2 rounded-lg">{error}</p>}

            {!isRecording && (
              <button onClick={() => handleAnalyze(null)} disabled={uploading || (!audioFiles || audioFiles.length === 0)} className="w-full mt-8 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:from-slate-400 disabled:to-slate-400 text-white font-bold py-4 px-4 rounded-xl flex items-center justify-center transition shadow-lg text-lg">
                {uploading ? 'Saving meeting…' : 'Transcribe & analyse locally'} <ChevronRight className="w-6 h-6 ml-2" />
              </button>
            )}
          </div>
        )}

        {/* Processing State */}
        {selectedMeetingId && ['queued', 'processing'].includes(meetingStatus) && (
          <div className="flex flex-col items-center justify-center h-full space-y-8 animate-fade-in pb-20 print:hidden">
            <div className="relative">
              <div className="absolute inset-0 border-4 border-indigo-200 rounded-full animate-ping opacity-30"></div>
              <div className="animate-spin rounded-full h-24 w-24 border-t-4 border-b-4 border-indigo-600 relative z-10"></div>
              <Mic2 className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-indigo-600 w-8 h-8 z-20" />
            </div>
            <div className="text-center">
              <h3 className="text-3xl font-extrabold text-slate-900 mb-3 tracking-tight">Processing your meeting…</h3>
              <p className="text-slate-500 max-w-md mx-auto text-lg leading-relaxed">Your recording is processed on this laptop. Completed transcription parts are saved automatically.</p>
              {jobProgress?.total_seconds > 0 && <div className="mt-4"><progress className="w-full" max={jobProgress.total_seconds} value={jobProgress.completed_seconds || 0} /><p>{formatTime(jobProgress.completed_seconds || 0)} / {formatTime(jobProgress.total_seconds)} transcribed</p></div>}
            </div>
            {!!preview?.transcript_segments?.length && <div className="w-full max-w-3xl rounded-xl border border-slate-200 bg-white p-5 max-h-96 overflow-y-auto">
              <h4 className="font-bold">Latest saved transcript — draft</h4>
              <p className="text-sm text-slate-500 mb-3">{preview.total_segments} passages saved. Review recognition against the recording; the final report will follow.</p>
              {preview.transcript_segments.map(segment => <p key={segment.segment_id} className="mb-2 break-words"><span className="text-slate-500 mr-2">{formatTime(segment.start)}</span>{segment.text}</p>)}
              {!!preview.events?.length && <p className="text-sm text-indigo-700 mt-3">{preview.events.length} event candidates in these passages.</p>}
            </div>}
          </div>
        )}

        {/* Dashboard State */}
        {selectedMeetingId && meetingStatus === 'completed' && reportData && (
          <div className="space-y-8 animate-fade-in max-w-5xl mx-auto pb-20 pt-2 print:space-y-6 print:pb-0 print:pt-0 print:max-w-none" id="printable-report">

            {/* Header */}
            <div className="flex items-end justify-between border-b border-slate-200 pb-6 print:border-b-2 print:border-black print:pb-4">
              <div>
                <h2 className="text-4xl font-black text-slate-900 tracking-tight print:text-black">{meetingTitle}</h2>
                <button className="text-sm underline print:hidden" onClick={async () => { const title = window.prompt('Meeting title', meetingTitle); if (!title?.trim()) return; try { await axios.post(`${API_URL}/meetings/${selectedMeetingId}/edit`, { title }); setMeetingTitle(title.trim()); fetchMeetings(); } catch { setError('Could not save the meeting title.'); } }}>Rename meeting</button>
                <p className="text-slate-500 font-mono text-sm mt-2 font-medium bg-slate-200 inline-block px-2 py-0.5 rounded text-slate-700 print:bg-transparent print:p-0 print:text-black">ID: {selectedMeetingId}</p>
              </div>
              <div className="flex space-x-3 print:hidden">
                <button onClick={() => window.print()} className="flex items-center space-x-2 px-4 py-2.5 bg-white hover:bg-slate-50 text-slate-700 rounded-lg font-bold transition shadow-sm border border-slate-200">
                  <Printer className="w-4 h-4" /><span>Print PDF</span>
                </button>
                <select aria-label="Export format" value={exportFormat} onChange={e => setExportFormat(e.target.value)} className="border rounded-lg p-2">{['json', 'md', 'txt', 'srt', 'vtt', 'csv'].map(f => <option key={f} value={f}>{f.toUpperCase()}</option>)}</select>
                <button onClick={exportReport} className="flex items-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold transition shadow-md">
                  <Download className="w-4 h-4" /><span>Export</span>
                </button>
              </div>
            </div>

            {/* Audio Player (If Available) - HIDDEN ON PRINT */}
            {audioUrl && (
              <div className="bg-slate-900 rounded-2xl shadow-xl border border-slate-800 p-5 flex items-center space-x-6 print:hidden">
                <div className="bg-indigo-500/20 p-3 rounded-xl border border-indigo-500/30">
                  <PlayCircle className="text-indigo-400 w-8 h-8" />
                </div>
                <div className="flex-1">
                  <p className="text-indigo-300 text-xs font-bold uppercase tracking-widest mb-2">Master Recording</p>
                  <audio ref={audioRef} controls src={audioUrl} className="w-full h-10 outline-none rounded-lg" style={{ filter: 'invert(100%) hue-rotate(180deg) brightness(1.2)' }} />
                </div>
              </div>
            )}

            <MeetingNotes key={selectedMeetingId} api={API_URL} id={selectedMeetingId} data={reportData} models={summaryModels} status={summaryStatus} progress={summaryProgress} error={summaryError} onQueued={() => { setSummaryStatus('queued'); setSummaryError(null); }} seek={seek} />

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 print:grid-cols-3 print:gap-2">
               <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center space-x-5 print:shadow-none print:border print:border-slate-300">
                 <div className="bg-indigo-50 p-4 rounded-2xl print:hidden"><Users className="text-indigo-600 w-6 h-6" /></div>
                 <div><p className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-1 print:text-black">Participants</p><p className="text-3xl font-black text-slate-800 print:text-black">{reportData.processing?.speaker_separation === false ? "Unknown" : reportData.participants?.length || 0}</p></div>
               </div>
               <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center space-x-5 print:shadow-none print:border print:border-slate-300">
                 <div className="bg-emerald-50 p-4 rounded-2xl print:hidden"><CheckCircle className="text-emerald-600 w-6 h-6" /></div>
                 <div><p className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-1 print:text-black">Decisions</p><p className="text-3xl font-black text-slate-800 print:text-black">{reportData.executive_summary?.num_confirmed_decisions || 0}</p></div>
               </div>
               <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center space-x-5 print:shadow-none print:border print:border-slate-300">
                 <div className="bg-amber-50 p-4 rounded-2xl print:hidden"><Kanban className="text-amber-600 w-6 h-6" /></div>
                 <div><p className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-1 print:text-black">Action Items</p><p className="text-3xl font-black text-slate-800 print:text-black">{reportData.action_items?.length || 0}</p></div>
               </div>
            </div>

            {/* Influence Roster Editor */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden print:shadow-none print:border print:border-slate-300 print:rounded-none">
              <div className="px-8 py-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between print:bg-white print:border-b-2 print:border-black">
                <div className="flex items-center space-x-3"><BarChart3 className="w-5 h-5 text-indigo-600 print:hidden" /><h3 className="font-bold text-slate-800 text-lg print:text-black">Speaker roster · estimates</h3></div>
              </div>
              <div className="p-0 overflow-y-auto max-h-72 print:max-h-none print:overflow-visible">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-white sticky top-0 border-b border-slate-200 shadow-sm text-slate-500 text-xs uppercase tracking-wider font-bold print:text-black print:border-b-2 print:shadow-none print:static">
                    <tr><th className="px-8 py-4">Speaker Identity</th><th className="px-8 py-4">Inferred Roles</th><th className="px-8 py-4">Influence estimate</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 print:divide-slate-300">
                    {reportData.participants && [...reportData.participants].sort((a, b) => (b.influence_score || 0) - (a.influence_score || 0)).map((data) => {
                      const speaker = data.speaker_id;
                      const displayName = speakerNames[speaker] || speaker;
                      return (
                      <tr key={speaker} className="hover:bg-slate-50 transition group print:hover:bg-white">
                        <td className="px-8 py-5 font-bold text-indigo-600 text-base print:text-black">
                          {editingSpeaker === speaker ? (
                            <div className="flex items-center space-x-2 print:hidden">
                              <input autoFocus type="text" className="border-2 border-indigo-400 rounded-lg px-3 py-1.5 text-sm w-40 outline-none focus:ring-2 focus:ring-indigo-500 font-semibold" value={editNameValue} onChange={(e) => setEditNameValue(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && saveSpeakerName(speaker)}/>
                              <button onClick={() => saveSpeakerName(speaker)} className="text-white bg-emerald-500 p-1.5 hover:bg-emerald-600 rounded-lg shadow-sm"><Check className="w-4 h-4"/></button>
                            </div>
                          ) : (
                            <div className="flex items-center space-x-3 cursor-pointer print:cursor-auto" onClick={() => { setEditingSpeaker(speaker); setEditNameValue(displayName); }}>
                              <div className="bg-indigo-100 p-1.5 rounded-md print:hidden"><User className="w-4 h-4 text-indigo-600" /></div>
                              <span>{displayName}</span>
                              <Edit2 className="w-4 h-4 text-slate-300 opacity-0 group-hover:opacity-100 transition print:hidden" />
                            </div>
                          )}
                        </td>
                        <td className="px-8 py-5 text-slate-500 font-medium print:text-black">{data.roles && data.roles.length > 0 ? data.roles.join(', ') : 'Participant'}</td>
                        <td className="px-8 py-5 text-slate-800 font-mono font-bold text-lg print:text-black">{Math.round((data.influence_score || 0) * 100)}</td>
                      </tr>
                    )})}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Tabbed View: Highlights vs Transcript - HIDDEN ON PRINT */}
            <div className="mt-10 border-b border-slate-200 print:hidden">
              <nav className="flex space-x-10">
                <button onClick={() => setReportViewTab('highlights')} className={`pb-4 px-2 font-bold text-sm transition border-b-4 ${reportViewTab === 'highlights' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'}`}>
                  Meeting Highlights
                </button>
                <button onClick={() => setReportViewTab('transcript')} className={`pb-4 px-2 font-bold text-sm transition border-b-4 flex items-center space-x-2 ${reportViewTab === 'transcript' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'}`}>
                  <AlignLeft className="w-4 h-4" /> <span>Full Transcript</span>
                </button>
              </nav>
            </div>

            {/* Highlights Content - ALWAYS BLOCK ON PRINT */}
            <div className={`bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden animate-fade-in print:shadow-none print:border-none print:rounded-none print:block print:mt-10 ${reportViewTab === 'highlights' ? 'block' : 'hidden'}`}>
                <div className="px-8 py-5 border-b border-slate-200 bg-slate-50 flex items-center space-x-3 print:bg-white print:border-b-2 print:border-black print:px-0">
                  <MessageSquare className="w-5 h-5 text-indigo-600 print:hidden" />
                  <h3 className="font-bold text-slate-800 text-2xl print:text-black">Decision Candidates</h3>
                </div>
                <div className="p-8 space-y-6 print:px-0">
                  {reportData.executive_summary?.confirmed_decisions && reportData.executive_summary.confirmed_decisions.length > 0 ? (
                    <div className="space-y-5">
                      {reportData.executive_summary.confirmed_decisions.map((dec, i) => {
                        const context = findContext(dec.final_decision);
                        return (
                        <div key={i} className="p-6 bg-emerald-50 border border-emerald-100 rounded-2xl relative overflow-hidden shadow-sm hover:shadow transition print:border print:border-slate-400 print:bg-white print:shadow-none print:rounded-none">
                          <div className="absolute top-0 left-0 w-1.5 bottom-0 bg-emerald-500 print:hidden"></div>
                          <h4 className="font-black text-emerald-800 mb-2 text-xs uppercase tracking-widest print:text-black">Decision {i+1}</h4>
                          <p className="text-emerald-950 font-medium text-lg leading-relaxed print:text-black">"{dec.final_decision}"</p>

                          {context && (
                            <div className="mt-4 pt-4 border-t border-emerald-200/50">
                              <p className="text-xs font-bold uppercase tracking-widest text-emerald-700/70 mb-2 print:text-slate-500">Transcript Context</p>
                              <div className="space-y-2 bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/10 print:bg-white print:border-slate-200">
                                {context.map((seg, idx) => {
                                   const speakerName = speakerNames[seg.speaker] || seg.speaker;
                                   return (
                                     <div key={idx} className={`text-sm leading-relaxed ${seg.isTarget ? 'font-black text-emerald-900 print:text-black' : 'text-emerald-700/70 font-medium print:text-slate-600'}`}>
                                       <span className="font-semibold uppercase tracking-wide mr-2 text-xs opacity-70">{speakerName}:</span>
                                       {seg.text}
                                     </div>
                                   )
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      )})}
                    </div>
                  ) : (
                    <div className="p-8 bg-slate-50 rounded-2xl text-slate-500 text-sm text-center border-2 border-dashed border-slate-200 font-medium print:bg-white print:text-black print:border-solid">No decision candidates extracted.</div>
                  )}
                </div>
            </div>

            {/* Action Items Content - ALWAYS BLOCK ON PRINT */}
            <div className={`bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden animate-fade-in print:shadow-none print:border-none print:rounded-none print:block print:mt-10 ${reportViewTab === 'highlights' ? 'block mt-8' : 'hidden'}`}>
                <div className="px-8 py-5 border-b border-slate-200 bg-slate-50 flex items-center space-x-3 print:bg-white print:border-b-2 print:border-black print:px-0">
                  <Kanban className="w-5 h-5 text-amber-600 print:hidden" />
                  <h3 className="font-bold text-slate-800 text-2xl print:text-black">Action Items</h3>
                </div>
                <div className="p-8 space-y-6 print:px-0">
                  {reportData.action_items && reportData.action_items.length > 0 ? (
                    <div className="space-y-5">
                      {reportData.action_items.map((task, i) => {
                         const assigneeName = task.speaker ? (speakerNames[task.speaker] || task.speaker) : 'Unassigned';
                         return (
                          <div key={i} className="p-6 bg-amber-50 border border-amber-100 rounded-2xl relative overflow-hidden shadow-sm hover:shadow transition print:border print:border-slate-400 print:bg-white print:shadow-none print:rounded-none">
                            <div className="absolute top-0 left-0 w-1.5 bottom-0 bg-amber-500 print:hidden"></div>
                            <div className="flex items-center space-x-2 mb-2">
                              <h4 className="font-black text-amber-800 text-xs uppercase tracking-widest print:text-black">Task {i+1}</h4>
                              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900 border border-amber-300 print:bg-transparent print:border-black print:text-black">Spoken by: {assigneeName}</span>
                            </div>
                            <p className="text-amber-950 font-medium text-lg leading-relaxed print:text-black">{task.text}</p>

                            {(() => {
                              const context = findContext(task.text);
                              if (!context) return null;
                              return (
                                <div className="mt-4 pt-4 border-t border-amber-200/50">
                                  <p className="text-xs font-bold uppercase tracking-widest text-amber-700/70 mb-2 print:text-slate-500">Transcript Context</p>
                                  <div className="space-y-2 bg-amber-500/5 p-4 rounded-xl border border-amber-500/10 print:bg-white print:border-slate-200">
                                    {context.map((seg, idx) => {
                                       const speakerName = speakerNames[seg.speaker] || seg.speaker;
                                       return (
                                         <div key={idx} className={`text-sm leading-relaxed ${seg.isTarget ? 'font-black text-amber-900 print:text-black' : 'text-amber-700/70 font-medium print:text-slate-600'}`}>
                                           <span className="font-semibold uppercase tracking-wide mr-2 text-xs opacity-70">{speakerName}:</span>
                                           {seg.text}
                                         </div>
                                       )
                                    })}
                                  </div>
                                </div>
                              );
                            })()}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="p-8 bg-slate-50 rounded-2xl text-slate-500 text-sm text-center border-2 border-dashed border-slate-200 font-medium print:bg-white print:text-black print:border-solid">No action items extracted.</div>
                  )}
                </div>
            </div>

            {/* Transcript Content - ALWAYS BLOCK ON PRINT */}
            <div className={`bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden animate-fade-in flex flex-col print:shadow-none print:border-none print:rounded-none print:block print:mt-10 print:h-auto ${reportViewTab === 'transcript' ? 'block max-h-[700px]' : 'hidden'}`}>
                <div className="px-8 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between print:bg-white print:border-b-2 print:border-black print:px-0">
                  <div className="flex items-center space-x-3">
                    <AlignLeft className="w-5 h-5 text-indigo-600 print:hidden" />
                    <h3 className="font-bold text-slate-800 text-2xl print:text-black">Full Meeting Transcript</h3>
                  </div>
                  <div className="relative print:hidden">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2" />
                    <input type="text" placeholder="Search transcript..." value={transcriptSearch} onChange={(e) => { setTranscriptSearch(e.target.value); setTranscriptPage(0); }} className="pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                  </div>
                </div>

                <div className="p-8 overflow-y-auto space-y-5 flex-1 custom-scrollbar print:p-0 print:overflow-visible print:max-h-none print:mt-6">
                  {reportData.transcript_segments && reportData.transcript_segments.length > 0 ? (
                    reportData.transcript_segments.filter(s => printing || s.text.toLowerCase().includes(transcriptSearch.toLowerCase()) || (speakerNames[s.speaker] || s.speaker).toLowerCase().includes(transcriptSearch.toLowerCase())).slice(printing ? 0 : transcriptPage * 100, printing ? undefined : (transcriptPage + 1) * 100).map((segment, i) => {
                      const speakerName = speakerNames[segment.speaker] || segment.speaker;
                      const hash = segment.speaker.split('').reduce((a,b)=>{a=((a<<5)-a)+b.charCodeAt(0);return a&a},0);
                      const colors = ['bg-blue-50 text-blue-900 border-blue-100', 'bg-indigo-50 text-indigo-900 border-indigo-100', 'bg-purple-50 text-purple-900 border-purple-100', 'bg-emerald-50 text-emerald-900 border-emerald-100'];
                      const colorClass = colors[Math.abs(hash) % colors.length];

                      return (
                        <div key={i} className="flex flex-col mb-4 print:break-inside-avoid">
                          <span className="text-xs font-black text-slate-400 uppercase tracking-wider mb-1.5 px-1 flex items-center print:text-black">
                            {speakerName} {typeof segment.confidence === 'number' && segment.confidence < .5 && <button onClick={() => seek(segment.start)} title="Low model score; this is not a calibrated accuracy probability" className="ml-2 normal-case underline text-amber-700">Review audio</button>} <span className="font-mono lowercase text-slate-400 ml-3 font-medium print:text-slate-600"><button onClick={() => seek(segment.start)} className="underline" aria-label="Play this transcript passage">{formatTime(segment.start)}</button></span>
                          </span>
                          <div className={`p-4 rounded-2xl rounded-tl-sm border inline-block max-w-[90%] shadow-sm ${colorClass} text-base leading-relaxed print:bg-transparent print:border-none print:p-0 print:shadow-none print:text-black print:max-w-full`}>
                            {segment.text}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-16 flex flex-col items-center justify-center text-slate-500 bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200 print:bg-white print:border-solid">
                      <MessageSquare className="w-12 h-12 text-slate-300 mb-4 print:hidden" />
                      <p className="font-medium text-lg print:text-black">No raw transcript available for this meeting.</p>
                    </div>
                  )}
                </div>
                <div className="flex gap-3 items-center p-3 border-t print:hidden">
                  <button disabled={transcriptPage === 0} onClick={() => setTranscriptPage(p => p - 1)} className="underline disabled:text-slate-400">Previous</button>
                  <span>Transcript page {transcriptPage + 1} · 100 passages per page</span>
                  <button disabled={(transcriptPage + 1) * 100 >= (reportData.transcript_segments || []).filter(s => s.text.toLowerCase().includes(transcriptSearch.toLowerCase()) || (speakerNames[s.speaker] || s.speaker).toLowerCase().includes(transcriptSearch.toLowerCase())).length} onClick={() => setTranscriptPage(p => p + 1)} className="underline disabled:text-slate-400">Next</button>
                </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}

export default App;
