export function pcmWav(samples) {
  const bytes = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(bytes);
  const text = (offset, value) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
  text(0, 'RIFF'); view.setUint32(4, bytes.byteLength - 8, true);
  text(8, 'WAVE'); text(12, 'fmt '); view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  text(36, 'data'); view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, i) => view.setInt16(44 + i * 2, Math.round(Math.max(-1, Math.min(1, sample)) * (sample < 0 ? 32768 : 32767)), true));
  return new Blob([bytes], { type: 'audio/wav' });
}

export async function startLivePreview(context, stream, send, update) {
  if (!context.audioWorklet || context.sampleRate !== 16000) throw new Error('Live preview requires AudioWorklet at 16 kHz. Full recording is available.');
  await context.audioWorklet.addModule('/recording-preview.js');
  const source = context.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(context, 'recording-preview');
  const mute = context.createGain(); mute.gain.value = 0;
  source.connect(node); node.connect(mute); mute.connect(context.destination);
  let busy = false;
  let closed = false;
  node.port.onmessage = async ({ data: { samples, offset } }) => {
    if (closed || samples.length < 16000) return;
    if (busy) { update({ status: 'Preview is behind; skipped a preview window. Full audio is still saved.' }); return; }
    busy = true;
    update({ status: 'Transcribing locally…' });
    try {
      const result = await send(pcmWav(samples));
      if (!closed) update({ status: 'Live draft · final analysis may revise text and speakers',
        segments: result.segments.map(s => ({ ...s, start: s.start + offset, end: s.end + offset })), language: result.language });
    } catch (error) {
      if (!closed) update({ status: error.response?.status === 429 ? 'Worker busy. Full recording is still saved.' : 'Preview unavailable. Save the recording for full analysis.' });
    } finally { busy = false; }
  };
  update({ status: 'Listening · first draft after 15 seconds plus processing time' });
  return { pause: value => node.port.postMessage(value ? 'pause' : 'resume'),
    stop: () => { closed = true; source.disconnect(); node.disconnect(); mute.disconnect(); node.port.close(); } };
}
