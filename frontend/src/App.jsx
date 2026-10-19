import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TaskReview from './TaskReview';
import { startLivePreview } from './livePreview';
import ProcessingPanel from './ProcessingPanel';
import { flushSync } from 'react-dom';
import { saveChunk, clearRecording, recordingExists, restoreRecording } from './recordingStore';
import { FileAudio, ChevronRight, Mic2, ShieldCheck, LayoutDashboard, History, Settings2, FileSliders }  from 'lucide-react';

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
  const [accountId, setAccountId] = useState('');

  // Local accounts do not send email or reset links.
  const [authView, setAuthView] = useState('login');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authSuccess, setAuthSuccess] = useState('');
  const [authBusy, setAuthBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState('');

  const [meetings, setMeetings] = useState([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [transcriptSearch, setTranscriptSearch] = useState('');
  const [preview, setPreview] = useState(null);

  const [audioFiles, setAudioFiles] = useState(null);
  const [pptFiles, setPptFiles] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(null);
  const [connectionError, setConnectionError] = useState(false);
  const [speakerFilter, setSpeakerFilter] = useState('');
  const [speakerCountCorrection, setSpeakerCountCorrection] = useState('');
  const meetingRequest = React.useRef(0);
  const pptInput = React.useRef(null);
  const [error, setError] = useState('');
  const [meetingTitle, setMeetingTitle] = useState('');
  const [speechModel, setSpeechModel] = useState('');
  const [speechModels, setSpeechModels] = useState([]);
  const [language, setLanguage] = useState('auto');
  const [vocabulary, setVocabulary] = useState('');
  const [diarization, setDiarization] = useState('auto');
  const [numSpeakers, setNumSpeakers] = useState('');
  const [jobProgress, setJobProgress] = useState(null);
  const [exportFormat, setExportFormat] = useState('md');
  const [transcriptPage, setTranscriptPage] = useState(0);
  const [printing, setPrinting] = useState(false);
  const audioRef = React.useRef(null);
  const selectedRef = React.useRef(null);

  const [reportData, setReportData] = useState(null);
  const [meetingRevision, setMeetingRevision] = useState('');
  const [meetingStatus, setMeetingStatus] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [reportViewTab, setReportViewTab] = useState('overview');

  const [screen, setScreen] = useState('home');
  const [notice, setNotice] = useState('');
  const [profile, setProfile] = useState({ name: '', role: '', organization: '' });
  const [meetingVocabulary, setMeetingVocabulary] = useState('');
  const [speakerRoles, setSpeakerRoles] = useState({});
  const [editRoleValue, setEditRoleValue] = useState('');
  const [speakerNames, setSpeakerNames] = useState({});
  const [editingSpeaker, setEditingSpeaker] = useState(null);
  const [editNameValue, setEditNameValue] = useState('');

  // --- Recording State ---
  const [isRecording, setIsRecording] = useState(false);
  const [liveDraft, setLiveDraft] = useState({ segments: [], status: '' });
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
  const [speakerSetup, setSpeakerSetup] = useState(null);
  const [canAnalyzeSpeakers, setCanAnalyzeSpeakers] = useState(false);
  const [analyzingSpeakers, setAnalyzingSpeakers] = useState(false);
  const timerRef = React.useRef(null);

  // --- Authentication Handlers ---
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    if (authBusy) return;
    setAuthError(''); setAuthSuccess('');
    if (authView === 'register' && authPassword !== confirmPassword) { setAuthError('Passwords do not match.'); return; }
    if (new TextEncoder().encode(authPassword).length > 72) { setAuthError('Use a password of at most 72 UTF-8 bytes.'); return; }
    setAuthBusy(true);
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
    } finally { setAuthBusy(false); }
  };

  const handleLogout = () => {
    if (mediaRecorderRef.current?.state !== 'inactive') mediaRecorderRef.current?.stop();
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
    setToken(null);
    setEmail(''); setAccountId(''); setScreen('home'); setProfile({}); setNotice('');
    selectedRef.current = null;
    setSelectedMeetingId(null); setReportData(null); setMeetingStatus(null); setMeetings([]);
  };

  // --- Data Fetching ---
  const fetchMeetings = async () => {
    const requestToken = localStorage.getItem('token');
    try {
      const res = await axios.get(`${API_URL}/meetings`);
      if (requestToken && requestToken === localStorage.getItem('token')) setMeetings(res.data.meetings);
    } catch (err) {
      if (err.response?.status === 401 && requestToken === localStorage.getItem('token')) handleLogout();
    }
  };

  useEffect(() => {
    if (!token) return;
    Promise.resolve().then(fetchMeetings);
    const interval = setInterval(fetchMeetings, 10000);
    return () => clearInterval(interval);
  }, [token]);

  const applyMeeting = snapshot => {
    setMeetingStatus(snapshot.status); setMeetingRevision(snapshot.revision || '');
    setProcessingStage(snapshot.stage); setMeetingTitle(snapshot.title);
    setJobProgress({ ...snapshot.progress, received_at: Date.now() }); setPreview(snapshot.preview);
    setCanAnalyzeSpeakers(snapshot.can_analyze_speakers); setConnectionError(false);
    if (snapshot.status === 'completed') {
      setReportData(snapshot.data); setAudioUrl(snapshot.audio_url);
      setSpeakerNames(snapshot.data?.speaker_names || {}); setSpeakerRoles(snapshot.data?.speaker_roles || {});
      setMeetingVocabulary(snapshot.data?.vocabulary || '');
    } else if (snapshot.status === 'failed') setError(snapshot.error || 'Meeting processing failed.');
  };

  useEffect(() => {
    if (!token || !selectedMeetingId || !['queued', 'processing'].includes(meetingStatus)) return;
    let active = true, timer;
    const controller = new AbortController();
    const generation = meetingRequest.current;
    const poll = async () => {
      let finished = false;
      try {
        const res = await axios.get(`${API_URL}/meetings/${selectedMeetingId}`, { signal: controller.signal });
        if (!active || selectedRef.current !== selectedMeetingId || generation !== meetingRequest.current) return;
        applyMeeting(res.data);
        finished = !['queued', 'processing'].includes(res.data.status);
        if (finished) fetchMeetings();
      } catch (err) {
        if (!active || axios.isCancel(err)) return;
        if (err.response?.status === 401) { handleLogout(); return; }
        setConnectionError(true);
      }
      if (active && !finished) timer = setTimeout(poll, 1500);
    };
    timer = setTimeout(poll, 1000);
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [selectedMeetingId, meetingStatus, token]);

  useEffect(() => {
    if (!token || !email) return;
    let active = true;
    Promise.resolve().then(() => {
      if (!active) return;
      try {
        const stored = JSON.parse(localStorage.getItem(`preferences:${email}`) || '{}');
        setLanguage(stored.language || 'auto'); setDiarization(stored.diarization || 'auto');
        if (stored.speechModel) setSpeechModel(stored.speechModel);
      } catch { /* Use defaults if saved preferences cannot be read. */ }
    });
    Promise.all([axios.get(`${API_URL}/auth/me`), axios.get(`${API_URL}/profile`)]).then(([identity, saved]) => {
      if (active) { setEmail(identity.data.email); setAccountId(identity.data.user_id); setProfile(saved.data); }
    }).catch(err => { if (active && err.response?.status === 401) handleLogout(); });
    return () => { active = false; };
  }, [token, email]);

  // --- App Actions ---
  const loadMeeting = async (id) => {
    selectedRef.current = id;
    const generation = ++meetingRequest.current;
    setMeetingStatus(null); setConnectionError(false); setSpeakerFilter(''); setSpeakerCountCorrection('');
    setSelectedMeetingId(id);
    setError(''); setNotice(''); setSpeakerRoles({}); setEditingSpeaker(null);
    setReportData(null);
    setPreview(null);
    setAudioUrl(null);
    setReportViewTab('overview');
    setTranscriptSearch('');
    setTranscriptPage(0); setJobProgress(null);
    try { setSpeakerNames(JSON.parse(localStorage.getItem(`speakerNames:${email}:${id}`) || '{}')); } catch { setSpeakerNames({}); }
    try {
      const res = await axios.get(`${API_URL}/meetings/${id}`);
      if (selectedRef.current !== id || generation !== meetingRequest.current) return;
      applyMeeting(res.data);
    } catch { if (selectedRef.current === id && generation === meetingRequest.current) setError("Failed to load meeting."); }
  };

  const handleAnalyze = async (overrideAudioFiles = null) => {
    const targetAudio = overrideAudioFiles || audioFiles;
    if (!targetAudio || targetAudio.length === 0) { setError("Audio file required."); return; }
    if (uploading) return;
    setError(''); setUploading(true); setUploadPercent(0);
    const formData = new FormData();
    formData.append('title', meetingTitle); formData.append('model_size', speechModel);
    formData.append('language', language); formData.append('vocabulary', vocabulary); formData.append('diarization', diarization);
    if (numSpeakers && diarization !== 'off') formData.append('num_speakers', numSpeakers);
    for(let i=0; i<targetAudio.length; i++) { formData.append('audio', targetAudio[i]); }
    if (pptFiles) { for(let i=0; i<pptFiles.length; i++) { formData.append('ppt', pptFiles[i]); } }
    try {
      const res = await axios.post(`${API_URL}/analyze`, formData, { onUploadProgress: event => setUploadPercent(event.total ? Math.round(event.loaded / event.total * 100) : null) });
      fetchMeetings(); await loadMeeting(res.data.meeting_id); setAudioFiles(null); setPptFiles(null); if (pptInput.current) pptInput.current.value = '';
      if (targetAudio[0]?.name.startsWith("meeting-recording")) { await clearRecording(); setHasDraft(false); }
    } catch (err) { const detail = err.response?.data?.detail; setError(typeof detail === 'string' ? detail : 'Upload failed. Check meeting settings; your saved recording is still available.'); } finally { setUploading(false); setUploadPercent(null); }
  };

  useEffect(() => {
    recordingExists().then(count => setHasDraft(count > 0)).catch(() => setError('Recording storage is unavailable. You can still upload audio.'));
    axios.get(`${API_URL}/health`).then(res => { setModelReady(res.data.asr_ready); setSpeechModels(res.data.asr_models || []); let stored = {}; try { stored = JSON.parse(localStorage.getItem(`preferences:${localStorage.getItem('userEmail')}`) || '{}'); } catch {} setSpeechModel(res.data.asr_models?.includes(stored.speechModel) ? stored.speechModel : res.data.asr_model || ''); setSpeakerSetup(res.data.diarization); }).catch(() => setModelReady(false));
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
    resources.live?.stop();
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
      const context = new AudioContext({ sampleRate: 16000 }); await context.resume();
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
      setLiveDraft({ segments: [], status: '' });
      try {
        recordingResources.current.live = await startLivePreview(context, stream, async blob => {
          const form = new FormData(); form.append('audio', blob, 'preview.wav');
          form.append('model_size', speechModel); form.append('language', language); form.append('vocabulary', vocabulary);
          return (await axios.post(`${API_URL}/recording/preview`, form, { timeout: 120000 })).data;
        }, update => setLiveDraft(previous => ({ ...previous, ...update,
          segments: [...previous.segments, ...(update.segments || [])].slice(-100) })));
      } catch (err) { setLiveDraft({ segments: [], status: err.message }); }
      recorder.start(5000);
      setIsRecording(true);
      setRecordingTime(0);
      timerRef.current = setInterval(() => { if (recorder.state === 'recording') setRecordingTime(time => time + 1); }, 1000);
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
    const roles = { ...speakerRoles, [speakerId]: editRoleValue };
    try { const saved = await axios.post(`${API_URL}/meetings/${meetingId}/edit`, { speaker_names: updated, speaker_roles: roles }); if (selectedRef.current === meetingId) { setMeetingRevision(saved.data.revision); setSpeakerNames(updated); setSpeakerRoles(roles); setEditingSpeaker(null); } }
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
    } catch (failure) {
      let detail = 'Report export failed.';
      try { const body = JSON.parse(await failure.response.data.text()); if (typeof body.detail === 'string') detail = body.detail; } catch { /* Keep the fallback for network failures. */ }
      setError(detail);
    }
  };

  const saveActionReview = async (eventId, values) => {
    const id = selectedMeetingId;
    const response = await axios.post(`${API_URL}/meetings/${id}/actions/${encodeURIComponent(eventId)}`, { ...values, revision: meetingRevision });
    if (selectedRef.current === id) {
      setMeetingRevision(response.data.revision);
      setReportData(previous => ({ ...previous, action_reviews: { ...previous?.action_reviews, [eventId]: response.data.action_review } }));
    }
  };

  const newMeeting = () => {
    selectedRef.current = null; meetingRequest.current++; setSelectedMeetingId(null); setReportData(null); setMeetingStatus(null);
    setAudioUrl(null); setMeetingTitle(''); setError(''); setNotice(''); setScreen('home');
  };
  const savePreferences = (key, value) => {
    try {
      const stored = JSON.parse(localStorage.getItem(`preferences:${email}`) || '{}');
      localStorage.setItem(`preferences:${email}`, JSON.stringify({ ...stored, [key]: value }));
    } catch { setError('Could not save this preference.'); }
  };
  const saveVocabulary = async () => {
    const id = selectedMeetingId;
    try {
      const saved = await axios.post(`${API_URL}/meetings/${id}/edit`, { vocabulary: meetingVocabulary });
      if (selectedRef.current === id) setMeetingRevision(saved.data.revision);
      if (selectedRef.current === id) {
        setReportData(data => ({ ...data, vocabulary: meetingVocabulary })); setNotice('Vocabulary saved with this meeting.');
      }
    } catch { setError('Could not save vocabulary.'); }
  };

  const filteredMeetings = meetings.filter(m => m.title.toLowerCase().includes(searchQuery.toLowerCase()));
  const segments = reportData?.transcript_segments || [];
  const normalizeSearch = value => String(value || '').normalize('NFKC').toLocaleLowerCase();
  const speakerLabel = speaker => speakerNames[speaker] || (speaker === 'UNKNOWN' || !speaker ? 'Speaker not identified' : /^SPEAKER_\d+$/.test(speaker) ? `Speaker ${Number(speaker.slice(8)) + 1}` : speaker);
  const visibleSegments = segments.filter(s => printing || ((!speakerFilter || s.speaker === speakerFilter) && [s.text, speakerLabel(s.speaker), speakerRoles[s.speaker]].some(value => normalizeSearch(value).includes(normalizeSearch(transcriptSearch)))));
  const highlightText = text => {
    if (!transcriptSearch.trim()) return text;
    const term = transcriptSearch.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return text.split(new RegExp(`(${term})`, 'giu')).map((part, index) => part.toLocaleLowerCase() === transcriptSearch.trim().toLocaleLowerCase() ? <mark key={index}>{part}</mark> : part);
  };
  const decisions = reportData?.decisions || [];
  const actions = (reportData?.action_items || []).map(item => ({ ...item, timestamp: item.timestamp_s ?? (typeof item.timestamp === 'number' ? item.timestamp : /^\d+:\d+:\d+$/.test(item.timestamp || '') ? item.timestamp.split(':').reduce((total, part) => total * 60 + Number(part), 0) : null) }));
  const participants = reportData?.participants || [];
  const influence = (reportData?.influence || []).map(person => ({ ...person, speaker_id: person.participant || person.speaker_id, score: person.influence_score ?? person.score }));
  const eventTimeline = reportData?.event_timeline || [];
  const panelVisible = name => printing || reportViewTab === name;


  const languageLabel = code => ({ en: 'English', hi: 'Hindi', auto: 'Automatic' }[code] || code || 'Language unavailable');
  const speakerRole = speaker => speakerRoles[speaker] || participants.find(p => p.speaker_id === speaker)?.roles?.join(', ').replaceAll('_', ' ') || '';
  const featureKeys = [['proposal_contribution', 'proposal', 'Proposals'], ['evidence_contribution', 'evidence', 'Evidence'], ['objection_contribution', 'objection', 'Challenges'], ['revision_contribution', 'revision', 'Revisions'], ['decision_contribution', 'decision', 'Decisions'], ['interaction_contribution', 'interaction', 'Interactions'], ['slide_grounded_contribution', 'slide_grounding', 'Slide grounding']];
  const decisionEvidence = decision => {
    const ids = new Set([decision.proposal_event_id, decision.final_decision_event_id, ...[...(decision.evidence_items || []), ...(decision.revisions || []), ...(decision.agreements || []), ...(decision.objections || [])].map(item => item.event_id)]);
    return eventTimeline.filter(event => ids.has(event.event_id)).sort((a, b) => a.start - b.start);
  };
  const analyzeSpeakers = async (automatic = false) => {
    const id = selectedMeetingId; setAnalyzingSpeakers(true);
    try {
      await axios.post(`${API_URL}/meetings/${id}/analyze-speakers`, { ...(automatic === true ? { automatic: true } : speakerCountCorrection ? { num_speakers: Number(speakerCountCorrection) } : {}), revision: meetingRevision });
      if (selectedRef.current === id) { setMeetingStatus('queued'); setProcessingStage('queued'); setReportData(null); setJobProgress(null); setPreview(null); setSpeakerNames({}); setSpeakerRoles({}); setNotice('Speaker analysis queued. Your recording and meeting title are saved.'); }
    } catch (err) { setError(err.response?.data?.detail || 'Could not start speaker analysis.'); }
    finally { setAnalyzingSpeakers(false); }
  };


  if (!token) return <div className="auth-shell"><section className="auth-card"><span className="privacy-badge"><ShieldCheck aria-hidden="true" /> Offline meeting workspace</span>
    <div className="brand"><Mic2 aria-hidden="true" /> InfluenceIQ</div>
    <h1>{authView === 'register' ? 'Create your account' : 'Welcome back'}</h1>
    <p className="muted">Use the same account in the Android app. Published meetings are saved on this server.</p>
    {authError && <p role="alert" className="notice error">{authError}</p>}
    {authSuccess && <p role="status" className="notice">{authSuccess}</p>}
    <form onSubmit={handleAuthSubmit} className="stack" aria-busy={authBusy}>
      <label>Email<input type="email" autoComplete="username" required disabled={authBusy} value={authEmail} onChange={e => setAuthEmail(e.target.value)} placeholder="you@example.com" /></label>
      <label>Password<input type={showPassword ? 'text' : 'password'} autoComplete={authView === 'register' ? 'new-password' : 'current-password'} required disabled={authBusy} minLength={authView === 'register' ? 8 : 1} maxLength={64} value={authPassword} onChange={e => setAuthPassword(e.target.value)} /></label>
      <button className="text-button password-toggle" type="button" aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Hide password' : 'Show password'}</button>
      {authView === 'register' && <><label>Confirm password<input type={showPassword ? 'text' : 'password'} autoComplete="new-password" required disabled={authBusy} maxLength={64} value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} /></label><p className="small muted">Use at least 8 characters. This account works on this server and the connected Android app.</p></>}
      <button className="primary" disabled={authBusy} type="submit">{authBusy ? 'Please wait…' : authView === 'register' ? 'Create Account' : 'Sign in'}</button>
    </form>
    <button disabled={authBusy} className="text-button" onClick={() => { setAuthPassword(''); setConfirmPassword(''); setShowPassword(false); setAuthView(authView === 'login' ? 'register' : 'login'); setAuthError(''); }}>{authView === 'login' ? 'Register' : 'I already have an account'}</button>
    {authView === 'login' && <details className="muted small"><summary>Account recovery</summary><p>On this laptop, run the password-recovery command in the README. No email is sent.</p></details>}
  </section></div>;

  return <div className="meeting-app">
    <header className="app-header print:hidden">
      <button className="brand text-button" onClick={newMeeting} disabled={isRecording}><Mic2 aria-hidden="true" /> InfluenceIQ</button>
      <nav aria-label="Main navigation">
        <button aria-current={screen === 'home' && !selectedMeetingId ? 'page' : undefined} disabled={isRecording} onClick={newMeeting}><LayoutDashboard aria-hidden="true" />Home</button>
        <button aria-current={screen === 'history' ? 'page' : undefined} disabled={isRecording} onClick={() => { setScreen('history'); fetchMeetings(); }}><History aria-hidden="true" />History</button>
        <button aria-current={screen === 'settings' ? 'page' : undefined} disabled={isRecording} onClick={() => setScreen('settings')}><Settings2 aria-hidden="true" />Settings</button>
      </nav><div className="workspace-privacy"><ShieldCheck aria-hidden="true" /><strong>Private workspace</strong><span>Audio processed on this laptop</span></div>
    </header>
    <main className="app-content">
      {error && <div role="alert" className="notice error"><span>{error}</span><button className="text-button" onClick={() => setError('')}>Dismiss</button></div>}
      {notice && <div role="status" className="notice"><span>{notice}</span><button className="text-button" onClick={() => setNotice('')}>Dismiss</button></div>}
      {screen === 'settings' ? <div className="stack settings-page print:hidden">
        <div><h1>Settings</h1><p className="muted">Set up once. Start meetings with fewer steps.</p></div>
        <section className="panel stack"><h2>Your profile</h2><p className="muted small">Shared with the Android app when both use this server. {email}</p>
          <p className="small muted">Account ID: {accountId || 'Checking…'}</p>
          <p className="small muted">In Android, open Account &amp; sync and enter this server address: {new URL(/^https?:/.test(API_URL) ? API_URL : import.meta.env.VITE_LOCAL_API_ORIGIN || API_URL, window.location.href).origin}. Publish selected device meetings to see them in History. Downloads remain available offline.</p>
          <label>Name<input maxLength={100} value={profile.name || ''} onChange={e => setProfile({ ...profile, name: e.target.value })} /></label>
          <label>Your role<input maxLength={100} value={profile.role || ''} onChange={e => setProfile({ ...profile, role: e.target.value })} /></label>
          <label>Organisation<input maxLength={200} value={profile.organization || ''} onChange={e => setProfile({ ...profile, organization: e.target.value })} /></label>
          <button onClick={async () => { const current = localStorage.getItem('token'); try { const saved = await axios.get(`${API_URL}/profile`); if (current === localStorage.getItem('token')) { setProfile(saved.data); setNotice('Account profile refreshed.'); } } catch { setError('Could not refresh your account profile.'); } }}>Refresh account profile</button>
          <button className="primary" onClick={async () => { try { await axios.post(`${API_URL}/profile`, profile); setNotice('Profile saved.'); } catch { setError('Could not save your profile.'); } }}>Save profile</button>
        </section>
        <section className="panel stack"><h2>Language</h2>
          <label>Transcription language<select aria-label="Language" value={language} onChange={e => { setLanguage(e.target.value); savePreferences('language', e.target.value); }}><option value="auto">Automatic · Hindi / English</option><option value="en">English</option><option value="hi">Hindi</option></select></label>
          <p className="muted small">Automatic is recommended. Choose a language if detection needs help.</p>
        </section>
        <section className="panel stack"><h2>Speaker analysis</h2><p>{speakerSetup?.message || 'Checking local speaker setup…'}</p><p className="muted small">Automatic speaker clusters can split or merge people incorrectly. Use the expected speaker count when known, then review the transcript. Human names are not recognised automatically.</p></section>
        <details className="panel stack"><summary>Advanced audio settings</summary><div className="stack">
          <label>Speech model<select aria-label="Speech model" value={speechModel} onChange={e => { setSpeechModel(e.target.value); savePreferences('speechModel', e.target.value); }}>{!speechModels.length && <option value={speechModel}>{speechModel || 'No model installed'}</option>}{speechModels.map(m => <option key={m}>{m}</option>)}</select></label>
          <p className="muted small">Larger models may improve recognition and take more time. {modelReady === false ? 'Complete local model setup before analysing.' : 'Speech models are ready for local analysis.'}</p>
          <label>Speaker separation<select aria-label="Speaker separation" value={diarization} onChange={e => { setDiarization(e.target.value); savePreferences('diarization', e.target.value); }}><option value="auto">Automatic, when available</option><option value="required">Require speaker separation</option><option value="off">Off</option></select></label>
          <label>Expected speakers (optional)<input type="number" min={1} max={50} disabled={diarization === 'off'} value={numSpeakers} onChange={e => setNumSpeakers(e.target.value)} /></label>
          <label>Capture source<select value={captureSource} onChange={e => setCaptureSource(e.target.value)}><option value="mic">Microphone</option><option value="tab">Microphone + shared tab audio</option></select></label>
          <label>Microphone<select value={deviceId} onChange={e => setDeviceId(e.target.value)}><option value="">System default</option>{devices.filter(d => d.deviceId).map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Microphone ${i + 1}`}</option>)}</select></label>
        </div></details>
        <p className="muted small">Meeting audio and analysis stay on this laptop. Review important results against the recording.</p>
        <button onClick={handleLogout}>Sign out</button>
      </div> : screen === 'history' ? <div className="stack print:hidden">
        <div className="section-heading"><div><h1>History</h1><p className="muted">Recordings, results and your edits, saved together.</p></div><button className="primary" onClick={newMeeting}>New meeting</button></div>
        <label className="sr-only" htmlFor="history-search">Search meetings</label><input id="history-search" placeholder="Search meetings…" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
        {filteredMeetings.length ? <div className="stack">{filteredMeetings.map(m => <button className="history-row" key={m.id} onClick={() => { setScreen('home'); loadMeeting(m.id); }}><strong>{m.title}</strong><span>{m.created_at ? new Date(m.created_at).toLocaleDateString() + ' · ' : ''}{m.status === 'completed' ? 'Ready to review' : m.status === 'processing' ? 'Analysing' : m.status}</span><ChevronRight aria-hidden="true" /></button>)}</div> : <section className="panel"><h2>{meetings.length ? 'No matching meetings' : 'Your first meeting starts here'}</h2><p className="muted">Record or upload audio from Home.</p></section>}
      </div> : <>
        {!selectedMeetingId && <div className="stack new-meeting print:hidden">
          <div><p className="eyebrow">Private · on this laptop</p><h1>Capture the conversation.</h1><p className="muted">We’ll organise the transcript, actions and decisions.</p></div>
          {hasDraft && !isRecording && <div className="notice"><span>Recording saved on this device.</span><button onClick={recoverDraft}>Recover recording</button><button className="text-button" onClick={async () => { if (!window.confirm('Discard the saved recording?')) return; await clearRecording(); setHasDraft(false); setAudioFiles(null); }}>Discard</button></div>}
          <section className="panel stack">
            {isRecording ? <div className="recording-state"><span className="eyebrow">{isPaused ? 'Paused' : 'Recording'}</span><strong className="recording-time">{formatTime(recordingTime)}</strong><meter min="0" max="100" value={audioLevel} aria-label="Audio input level" /><p className="muted small">{audioLevel < 2 && !isPaused ? 'Move closer to the microphone if the room is quiet.' : 'Keep this tab open while recording.'}</p><div className="button-row"><button onClick={() => { const recorder = mediaRecorderRef.current; if (recorder?.state === 'recording') { recorder.pause(); recordingResources.current?.live?.pause(true); setIsPaused(true); } else if (recorder?.state === 'paused') { recorder.resume(); recordingResources.current?.live?.pause(false); setIsPaused(false); } }}>{isPaused ? 'Resume recording' : 'Pause recording'}</button><button className="primary" onClick={stopRecording}>Stop & Save</button></div></div> : <div className="capture-actions">
              <button className="capture primary" onClick={startRecording} disabled={uploading || hasDraft === null || hasDraft}><Mic2 aria-hidden="true" /><strong>Record meeting</strong><span>Use your microphone</span></button>
              <label className="capture upload"><FileAudio aria-hidden="true" /><strong>Upload audio</strong><span>WAV, MP3, M4A and more</span><input aria-label="Upload audio" type="file" multiple accept="audio/*,.mp4,.webm,.m4a,.flac,.aac,.ogg,.opus,.wma,.aiff,.aif,.amr,.3gp" disabled={uploading} onChange={e => setAudioFiles(Array.from(e.target.files))} /></label>
            </div>}
            {isRecording && <section className="notice" aria-label="Live transcription"><div><strong>Live transcription draft</strong><p role="status" className="small muted">{liveDraft.status}</p><p className="small muted">Preview uses 15-second windows. Full analysis after saving includes the entire recording, including any skipped windows. Speakers are not assigned in the live draft.</p>{liveDraft.segments.map((s, i) => <p key={`${s.start}:${i}`}><span className="muted">{formatTime(s.start)} · </span>{s.text}</p>)}</div></section>}
            {audioFiles?.length > 0 && !isRecording && <div><p className="small muted">{audioFiles.length} file(s) ready · parts play in the order below</p><ol className="stack">{Array.from(audioFiles).map((file, i) => <li key={`${file.name}:${i}`} className="file-row"><span>{file.name}</span><button aria-label={`Move ${file.name} up`} disabled={i === 0 || uploading} onClick={() => { const parts = Array.from(audioFiles); [parts[i - 1], parts[i]] = [parts[i], parts[i - 1]]; setAudioFiles(parts); }}>↑</button><button aria-label={`Remove ${file.name}`} disabled={uploading} onClick={() => setAudioFiles(Array.from(audioFiles).filter((_, j) => j !== i))}>Remove</button></li>)}</ol></div>}
            <label>Meeting title (optional)<input value={meetingTitle} maxLength={200} disabled={uploading} onChange={e => setMeetingTitle(e.target.value)} placeholder="Weekly planning…" /></label>
            <div className="attachment"><div className="section-heading"><div className="attachment-title"><FileSliders aria-hidden="true" /><div><strong>Presentation</strong><p className="small muted">Optional · PowerPoint (.pptx)</p></div></div><label className="file-picker" htmlFor="meeting-ppt">{pptFiles?.[0] ? 'Replace PPT' : 'Upload PPT'}</label><input className="visually-hidden" id="meeting-ppt" ref={pptInput} aria-label="Upload PPT" type="file" accept=".pptx" disabled={uploading || isRecording} onChange={e => { if (e.target.files.length) setPptFiles(Array.from(e.target.files)); }} /></div>{pptFiles?.[0] && <div className="file-row"><span>{pptFiles[0].name}</span><button type="button" disabled={uploading} onClick={() => { setPptFiles(null); if (pptInput.current) pptInput.current.value = ''; }}>Remove PPT</button></div>}</div>
            <div className="meeting-options"><label>Language<select aria-label="Meeting language" disabled={uploading} value={language} onChange={e => setLanguage(e.target.value)}><option value="auto">Auto · Hindi / English / Hinglish</option><option value="en">English</option><option value="hi">Hindi</option></select></label><label>Expected speakers (optional)<input aria-label="Expected speakers" type="number" min="1" max="50" placeholder="Auto-detect" disabled={uploading || diarization === 'off'} value={numSpeakers} onChange={e => setNumSpeakers(e.target.value)} /></label></div><p className="small muted">If you know the number of speakers, enter it to reduce incorrect speaker splits. Automatic detection needs review.</p>
            <details><summary>Vocabulary hints <span className="muted small">optional</span></summary><label className="stack small">Names and technical terms<textarea aria-label="Vocabulary hints" maxLength={1000} value={vocabulary} onChange={e => setVocabulary(e.target.value)} placeholder="Names, acronyms, unusual spellings…" /><span className="muted">You can leave this empty. Editable suggestions appear after analysis.</span></label></details>
            {!isRecording && <button className="primary" onClick={() => handleAnalyze()} disabled={uploading || !audioFiles?.length || modelReady === false}>{uploading ? uploadPercent === 100 ? 'Validating upload…' : `Uploading${uploadPercent != null ? ` ${uploadPercent}%` : '…'}` : 'Analyse meeting'}</button>}
            {uploading && <div aria-live="polite"><progress aria-label="Upload progress" max="100" {...(uploadPercent != null ? { value: uploadPercent } : {})} /><p className="small muted">{uploadPercent === 100 ? 'Upload received. Checking audio and presentation before processing…' : 'Sending files to your local backend…'}</p></div>}
            {modelReady === false && <p className="small muted">Analysis needs a local speech model. <button className="text-button" onClick={() => setScreen('settings')}>Open Settings</button></p>}
          </section>
          <p className="muted small">Language is automatic by default. Completed meetings are saved to History.</p>
          {!!meetings.length && <section><div className="section-heading"><h2>Recent meetings</h2><button className="text-button" onClick={() => setScreen('history')}>View history</button></div>{meetings.slice(0, 3).map(m => <button className="history-row" key={m.id} onClick={() => loadMeeting(m.id)}><strong>{m.title}</strong><span>{m.status === 'completed' ? 'Ready to review' : m.status}</span><ChevronRight aria-hidden="true" /></button>)}</section>}
        </div>}
        {selectedMeetingId && <div className="stack report-page">
          <div className="section-heading"><div><button className="text-button print:hidden" onClick={newMeeting}>← Home</button><h1>{meetingTitle || 'Your meeting'}</h1><p className="muted small">Saved in History</p></div><details className="meeting-menu print:hidden"><summary>Meeting options</summary><div className="stack"><button onClick={async () => { const title = window.prompt('Meeting title', meetingTitle); if (!title?.trim()) return; try { const saved = await axios.post(`${API_URL}/meetings/${selectedMeetingId}/edit`, { title }); setMeetingRevision(saved.data.revision); setMeetingTitle(title.trim()); fetchMeetings(); } catch { setError('Could not save the title.'); } }}>Rename meeting</button><button disabled={meetingStatus !== 'completed'} onClick={() => window.print()}>Print / save PDF</button><label>Export format<select aria-label="Export format" value={exportFormat} onChange={e => setExportFormat(e.target.value)}>{[['md', 'Meeting report'], ['txt', 'Plain text'], ['srt', 'Subtitles (SRT)'], ['vtt', 'Subtitles (VTT)'], ['csv', 'Transcript table'], ['ics', 'Reviewed task calendar (.ics)'], ['json', 'Data (JSON)']].map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label><button disabled={meetingStatus !== 'completed'} onClick={exportReport}>Export</button></div></details></div>
          {['queued', 'processing'].includes(meetingStatus) && <ProcessingPanel status={meetingStatus} stage={processingStage} progress={jobProgress} preview={preview} connectionError={connectionError} />}
          {meetingStatus === 'failed' && <section className="panel"><h2>Your recording is saved</h2><p className="muted">Analysis stopped. Retry to continue from saved progress.</p><button className="primary" onClick={async () => { try { await axios.post(`${API_URL}/meetings/${selectedMeetingId}/retry`); setMeetingStatus('queued'); setError(''); } catch { setError('Could not restart analysis.'); } }}>Retry analysis</button></section>}
          {meetingStatus === 'completed' && reportData && <>
            <nav className="result-tabs print:hidden" aria-label="Meeting results">{[['overview', 'Overview'], ['transcript', 'Transcript'], ['participants', 'Participants'], ['actions', 'Action items'], ['decisions', 'Decisions'], ['influence', 'Influence'], ['events', 'Events'], ['presentation', 'Presentation']].map(([key, label]) => <button key={key} aria-current={reportViewTab === key ? 'page' : undefined} onClick={() => { setReportViewTab(key); setNotice(''); }}>{label}</button>)}</nav>
            {audioUrl && <audio aria-label="Original meeting recording" ref={audioRef} controls src={audioUrl} className="meeting-audio print:hidden" />}
            {panelVisible('overview') && <>
              <section className="panel stack"><h2>At a glance</h2><div className="summary-stats"><div><strong>{formatTime(reportData.meeting_overview?.duration_s || 0)}</strong><span>Duration</span></div><div><strong>{participants.length}</strong><span>Speaker clusters</span></div><div><strong>{decisions.length}</strong><span>Decision candidates</span></div></div><p>{reportData.language_analysis?.label || languageLabel(reportData.processing?.language)}</p><p className="muted small">Structured NLP analysis. Review candidates and speaker assignments against the recording.</p>{(jobProgress?.elapsed_seconds ?? reportData.processing?.elapsed_seconds) != null && <div className="completion-timing"><span aria-hidden="true">✓</span>Processed in {formatTime(jobProgress?.elapsed_seconds ?? reportData.processing.elapsed_seconds)} · 100% complete</div>}</section>
              {!!reportData.processing?.warnings?.length && <section className="notice stack">{reportData.processing.warnings.map((warning, i) => <p key={i}>{warning}</p>)}</section>}
              {!participants.length && <section className="panel stack"><h2>Participant analysis needs speaker attribution</h2><p className="muted">This transcript has no identified speaker clusters. Names, roles and influence cannot be calculated until its speech is attributed.</p><button className="primary" disabled={!canAnalyzeSpeakers || !speakerSetup?.ready || analyzingSpeakers} onClick={analyzeSpeakers}>{analyzingSpeakers ? 'Starting speaker analysis…' : 'Analyse speakers from saved audio'}</button><p className="small muted">{!canAnalyzeSpeakers ? 'Saved source audio is unavailable. Upload the original recording again.' : !speakerSetup?.ready ? 'Complete local speaker setup in Settings first.' : 'This uses local speaker models, then rebuilds the transcript and NLP analysis.'}</p></section>}
              {!!participants.length && <details className="panel stack" open={participants.length > 20}><summary>Review speaker separation{participants.length > 20 ? ` · ${participants.length} clusters need checking` : ''}</summary><p className="small muted">Automatic clusters can split one person into many groups. Influence depends on accurate attribution. Enter the actual speaker count, or rerun automatically if it is unknown. Automatic results still need review. Review and re-enter names and roles afterward because speaker groups can change.</p><label>Actual number of speakers<input aria-label="Actual number of speakers" type="number" min="1" max="50" placeholder="Number of people speaking" value={speakerCountCorrection} onChange={e => setSpeakerCountCorrection(e.target.value)} /></label><button disabled={!speakerCountCorrection || Number(speakerCountCorrection) < 1 || Number(speakerCountCorrection) > 50 || analyzingSpeakers || !canAnalyzeSpeakers || !speakerSetup?.ready} onClick={analyzeSpeakers}>{analyzingSpeakers ? 'Starting…' : 'Reanalyse with this speaker count'}</button><button disabled={analyzingSpeakers || !canAnalyzeSpeakers || !speakerSetup?.ready} onClick={() => analyzeSpeakers(true)}>Reanalyse automatically · count unknown</button></details>}
              <section className="panel stack"><h2>Vocabulary</h2><p className="muted small">Review observed acronyms, technical terms, repeated names and terms from your slides. Common conversation words are excluded. Hints help future recognition; editing these does not change the saved transcript.</p>{!!reportData.vocabulary_suggestions?.length && <div className="term-list">{reportData.vocabulary_suggestions.map(term => <button key={term} onClick={() => setMeetingVocabulary(previous => Array.from(new Set([...previous.split(',').map(x => x.trim()).filter(Boolean), term])).join(', ').slice(0, 1000))}>{term}</button>)}</div>}<label>Meeting vocabulary<textarea aria-label="Meeting vocabulary" maxLength={1000} value={meetingVocabulary} onChange={e => setMeetingVocabulary(e.target.value)} placeholder="Add names or useful terms…" /></label><div className="button-row"><button onClick={saveVocabulary}>Save vocabulary</button><button onClick={() => { setVocabulary(meetingVocabulary); newMeeting(); setNotice('Vocabulary added to your next meeting hints.'); }}>Use for next meeting</button></div></section>
              <details className="panel stack"><summary>Language and evaluation</summary><div className="stack"><p>{reportData.language_analysis?.method || 'Automatic ASR language detection, scoped to Hindi / English.'}</p><p className="small muted">ASR language observations: {(reportData.language_analysis?.asr_languages || [reportData.processing?.language]).filter(Boolean).map(languageLabel).join(', ') || 'Not available'}</p><p className="small muted">{reportData.language_analysis?.limitations || 'A dominant language is not a measurement of code-switching accuracy.'}</p><strong>Accuracy has not been measured for this meeting.</strong><p className="muted small">WER needs a checked transcript; DER needs checked speaker times. Event/decision F1 and influence rankings need human annotations. Influence estimates are not accuracy scores.</p></div></details>
            </>}
            {panelVisible('transcript') && <section className="panel stack"><div className="section-heading"><h2>Transcript</h2><input aria-label="Search transcript" className="print:hidden" placeholder="Find in this meeting…" value={transcriptSearch} onChange={e => { setTranscriptSearch(e.target.value); setTranscriptPage(0); }} /></div><div className="section-heading print:hidden"><p className="small muted">{visibleSegments.length} of {segments.length} passages{transcriptSearch ? ' match your search' : ''}. Select a timestamp to hear the original audio.</p><label>Filter by speaker<select aria-label="Filter by speaker" value={speakerFilter} onChange={e => { setSpeakerFilter(e.target.value); setTranscriptPage(0); }}><option value="">All speakers</option>{Array.from(new Set(segments.map(s => s.speaker))).map(speaker => <option key={speaker} value={speaker}>{speakerLabel(speaker)}</option>)}</select></label>{(transcriptSearch || speakerFilter) && <button onClick={() => { setTranscriptSearch(''); setSpeakerFilter(''); setTranscriptPage(0); }}>Clear search</button>}</div>{!visibleSegments.length && <p className="muted">{segments.length ? 'No matching passages.' : 'No speech was transcribed. Check the recording.'}</p>}{visibleSegments.slice(printing ? 0 : transcriptPage * 100, printing ? undefined : (transcriptPage + 1) * 100).map(s => <article className="passage" key={s.segment_id}><div className="passage-heading"><div><strong>{speakerLabel(s.speaker)}</strong>{speakerRole(s.speaker) && <div className="muted small">{speakerRole(s.speaker)}</div>}</div><button aria-label="Play this transcript passage" className="text-button print:hidden" onClick={() => seek(s.start)}>{formatTime(s.start)}</button></div><p>{highlightText(s.text)}</p>{typeof s.confidence === 'number' && s.confidence < .5 && <button className="text-button small print:hidden" onClick={() => seek(s.start)}>Review audio</button>}</article>)}{visibleSegments.length > 100 && <div className="pager print:hidden"><button disabled={transcriptPage === 0} onClick={() => setTranscriptPage(p => p - 1)}>Previous</button><span>Page {transcriptPage + 1} of {Math.ceil(visibleSegments.length / 100)}</span><button disabled={(transcriptPage + 1) * 100 >= visibleSegments.length} onClick={() => setTranscriptPage(p => p + 1)}>Next</button></div>}</section>}
            {panelVisible('participants') && <section className="panel stack"><h2>Participants</h2><p className="muted small">Speaker clusters come from audio. Names come from explicit self-introductions when available; review or enter them yourself. Estimated roles describe observed contributions, not job titles.</p>{!participants.length && <p>Speaker attribution is unavailable. Return to Overview to analyse the saved audio.</p>}{participants.map(person => <article className="passage stack" key={person.speaker_id}><div className="section-heading"><strong>{speakerLabel(person.speaker_id)}</strong><span>{typeof person.speaking_duration_s === 'number' ? `${formatTime(person.speaking_duration_s)} spoken` : 'Speaking time unavailable'}</span></div>{reportData.speaker_name_sources?.[person.speaker_id]?.method === 'explicit_self_introduction' && speakerNames[person.speaker_id] === reportData.speaker_name_sources[person.speaker_id].name && <p className="small muted">Name detected from a self-introduction; verify against the recording. <button className="text-button" onClick={() => seek(reportData.speaker_name_sources[person.speaker_id].start || 0)}>Listen to introduction</button></p>}{editingSpeaker === person.speaker_id ? <><label>Speaker name<input aria-label="Speaker name" maxLength={100} value={editNameValue} onChange={e => setEditNameValue(e.target.value)} /></label><label>Meeting role<input aria-label="Meeting role" maxLength={100} value={editRoleValue} onChange={e => setEditRoleValue(e.target.value)} placeholder="Your description of their contribution" /></label><div className="button-row"><button onClick={() => saveSpeakerName(person.speaker_id)}>Save speaker</button><button onClick={() => setEditingSpeaker(null)}>Cancel</button></div></> : <><p className="muted small">{speakerRoles[person.speaker_id] ? `Your role label: ${speakerRoles[person.speaker_id]}` : `Estimated roles: ${speakerRole(person.speaker_id) || 'Not determined'}`}</p><p className="small muted">{person.num_turns ?? '—'} transcript passages · {person.decision_linked_events ?? '—'} decision-linked events</p><button className="text-button print:hidden" onClick={() => { setEditingSpeaker(person.speaker_id); setEditNameValue(speakerNames[person.speaker_id] || ''); setEditRoleValue(speakerRoles[person.speaker_id] || ''); }}>Edit name & role</button></>}</article>)}</section>}
            {panelVisible('actions') && <section className="panel stack"><h2>Action items</h2><p className="muted small">Extracted commitments and task candidates. The person who speaks a task is not automatically its owner. Review tasks below, then export confirmed open deadlines using Meeting options → Reviewed task calendar.</p>{actions.length ? actions.map((task, i) => <article className="passage" key={task.event_id || i}><p>{task.text}</p><div className="passage-heading"><span className="muted small">{speakerLabel(task.speaker)}{speakerRole(task.speaker) && ` · ${speakerRole(task.speaker)}`}</span>{typeof task.timestamp === 'number' && <button className="text-button" onClick={() => seek(task.timestamp)}>Listen at {formatTime(task.timestamp)}</button>}</div><TaskReview task={task} review={reportData.action_reviews?.[task.event_id]} onSave={saveActionReview} /></article>) : <p className="muted">No action candidates found.</p>}</section>}
            {panelVisible('decisions') && <section className="panel stack"><h2>Decision table</h2><p className="muted small">Rule-based reconstruction. Open a decision to review the proposal, discussion and source evidence.</p>{decisions.length ? <div className="table-scroll"><table><thead><tr><th>Decision / proposal</th><th>Participants</th><th>Status & lineage</th></tr></thead><tbody>{decisions.map((d, i) => <tr key={d.decision_id || i}><td>{d.final_decision_text || d.proposal_text || d.topic || 'Unresolved discussion'}{d.proposal_speaker && <p className="small muted">Proposed by {speakerLabel(d.proposal_speaker)}{speakerRole(d.proposal_speaker) && ` · ${speakerRole(d.proposal_speaker)}`}</p>}</td><td>{d.participants?.map(speaker => <p className="small" key={speaker}>{speakerLabel(speaker)}{speakerRole(speaker) && <span className="muted"> · {speakerRole(speaker)}</span>}</p>) || 'Unavailable'}</td><td>{d.status === 'confirmed' ? 'Decision candidate' : d.status}<details><summary>Source & lineage</summary>{decisionEvidence(d).map(event => <article className="evidence-row" key={event.event_id}><strong className="small">{event.event_type.replaceAll('_', ' ')} · {speakerLabel(event.speaker)}</strong><p className="small">{event.text}</p><button className="text-button" onClick={() => seek(event.start)}>Listen at {formatTime(event.start)}</button></article>)}{!decisionEvidence(d).length && <p className="small muted">No source events available in this saved report.</p>}{d.supporting_segments?.length > 0 && <button className="text-button" onClick={() => { const segment = segments.find(s => d.supporting_segments.includes(s.segment_id)); if (segment) seek(segment.start); }}>Listen to source</button>}</details></td></tr>)}</tbody></table></div> : <p className="muted">No decision candidates found.</p>}</section>}
            {panelVisible('influence') && <section className="panel stack"><h2>Influence & evidence</h2><p className="muted">Decision-linked contribution estimates. Speaking time is shown separately and does not define influence. Scores depend on speaker separation and NLP coverage; they are not percentages or performance ratings.</p>{participants.length > 20 && <p className="notice error">Speaker clustering needs review. Return to Overview and set the actual speaker count before interpreting these scores.</p>}{!influence.length && <p>No influence records are available. Identified speakers and processed NLP events are required.</p>}{influence.map(person => <article className="passage stack" key={person.speaker_id}><div className="section-heading"><div><strong>{speakerLabel(person.speaker_id)}</strong><p className="muted small">{speakerRole(person.speaker_id) || 'Role not determined'}</p></div><strong>{typeof person.score === 'number' ? `${person.score.toFixed(2)} / 1` : 'Unavailable'}</strong></div>{typeof person.score === 'number' && <meter min="0" max="1" value={person.score} aria-label={`Influence estimate for ${speakerLabel(person.speaker_id)}`} />}{person.score === 0 && <p className="small muted">No scored decision-linked contribution was detected. This does not mean this person had no influence.</p>}{person.explanation?.map((text, i) => <p className="small" key={i}>{text}</p>)}<details><summary>Score breakdown & evidence</summary><div className="stack"><div className="table-scroll"><table><thead><tr><th>Contribution</th><th>Raw</th><th>Normalised</th><th>Weight</th></tr></thead><tbody>{featureKeys.map(([key, weightKey, label]) => <tr key={key}><td>{label}</td><td>{person.raw_features?.[key] ?? '—'}</td><td>{typeof person.features?.[key] === 'number' ? person.features[key].toFixed(2) : '—'}</td><td>{reportData.influence_method?.weights?.[weightKey] ?? '—'}</td></tr>)}</tbody></table></div>{(person.supporting_events || []).map(id => eventTimeline.find(event => event.event_id === id)).filter(Boolean).map(event => <article className="evidence-row" key={event.event_id}><p>{event.text}</p><span className="small muted">{speakerLabel(event.speaker)} · {event.event_type.replaceAll('_', ' ')}{event.slide_id && ` · ${event.slide_id}`}</span><button className="text-button" onClick={() => seek(event.start)}>Listen at {formatTime(event.start)}</button></article>)}{!person.supporting_events?.length && <p className="small muted">No decision-linked source events found for this participant.</p>}</div></details></article>)}<p className="muted small">{reportData.influence_method?.disclaimer || 'Prototype weights and max normalisation. Human ratings are needed to validate these estimates; scores do not establish causal influence.'}</p></section>}
            {panelVisible('events') && <section className="panel stack"><h2>Events & interactions</h2><p className="muted small">Observed proposals, objections, evidence, corrections, agreements and other event candidates.</p>{!eventTimeline.length && <p>No saved event timeline is available.</p>}{eventTimeline.map(event => <article className="passage" key={event.event_id}><div className="passage-heading"><strong>{event.event_type.replaceAll('_', ' ')}</strong><button className="text-button" onClick={() => seek(event.start)}>{formatTime(event.start)}</button></div><p>{event.text}</p><p className="muted small">{speakerLabel(event.speaker)}{speakerRole(event.speaker) && ` · ${speakerRole(event.speaker)}`}{event.slide_id && ` · ${event.slide_id}`}</p></article>)}{!!reportData.interactions?.relationships?.length && <details><summary>Interaction relationships</summary>{reportData.interactions.relationships.map((edge, i) => <p className="small" key={i}>{speakerLabel(edge.source_speaker)} → {speakerLabel(edge.target_speaker)} · {edge.interaction_type?.replaceAll('_', ' ') || 'interaction'}</p>)}</details>}</section>}
            {panelVisible('presentation') && <section className="panel stack"><h2>Presentation & alignment</h2><p className="muted small">Slide text, tables, optional OCR and existing audio–PPT similarity links. A related slide is not proof that a spoken claim is true.</p>{!reportData.slides?.length && <p>No analysed presentation is available. Add a PPTX when uploading your next meeting.</p>}{reportData.slides?.map(slide => <article className="passage stack" key={slide.slide_id}><h3>Slide {slide.slide_number} · {slide.title || slide.slide_id}</h3>{!!slide.metadata?.ocr?.length && <p className="small muted">Includes text recognized from slide images. Review the original slide for OCR errors.</p>}{slide.text?.map((text, i) => <p key={i}>{text}</p>)}{slide.tables?.map((table, i) => <div className="table-scroll" key={i}><table><tbody>{table.rows.map((row, j) => <tr key={j}>{row.map((value, k) => <td key={k}>{value}</td>)}</tr>)}</tbody></table></div>)}<details><summary>Linked discussion</summary>{reportData.aligned_segments?.filter(segment => segment.slide_id === slide.slide_id).map(segment => <article className="evidence-row" key={segment.segment_id}><p>{segment.text}</p><p className="small muted">{speakerLabel(segment.speaker)}{speakerRole(segment.speaker) && ` · ${speakerRole(segment.speaker)}`}{typeof segment.alignment_score === 'number' && ` · similarity ${segment.alignment_score.toFixed(2)}`}</p><button className="text-button" onClick={() => seek(segment.start)}>Listen at {formatTime(segment.start)}</button></article>)}</details></article>)}{!!reportData.consistency_checks?.flags?.length && <section className="notice stack"><h3>Possible quantity mismatches · review required</h3>{reportData.consistency_checks.flags.map((flag, i) => <div key={i}><p>{flag.statement}</p><p className="small">{flag.slide_id}: {flag.slide_text}</p><p className="small">Spoken {flag.spoken_value} vs slide {flag.slide_value} {flag.unit}</p><button className="text-button" onClick={() => seek(flag.start)}>Listen to claim</button></div>)}</section>}<p className="small muted">{reportData.consistency_checks?.limitations || 'Slide inconsistencies have not been evaluated for this saved report. Image meaning is not evaluated; optional OCR reads text only.'}</p></section>}
          </>}
        </div>}
      </>}
    </main>
  </div>;
}
export default App;
