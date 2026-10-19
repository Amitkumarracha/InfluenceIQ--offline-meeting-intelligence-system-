/* Fixed-size PCM windows. The original MediaRecorder stream remains the source of truth. */
class RecordingPreview extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(sampleRate * 15);
    this.used = 0;
    this.offset = 0;
    this.paused = false;
    this.port.onmessage = ({ data }) => {
      if (data === 'flush') this.flush();
      else this.paused = data === 'pause';
    };
  }
  flush() {
    if (!this.used) return;
    const samples = this.buffer.slice(0, this.used);
    this.port.postMessage({ samples, offset: this.offset / sampleRate }, [samples.buffer]);
    this.offset += this.used;
    this.used = 0;
  }
  process(inputs) {
    if (!this.paused && inputs[0]?.length) {
      const channels = inputs[0];
      for (let i = 0; i < channels[0].length; i++) {
        let value = 0;
        for (const channel of channels) value += channel[i];
        this.buffer[this.used++] = value / channels.length;
        if (this.used === this.buffer.length) this.flush();
      }
    }
    return true;
  }
}
registerProcessor('recording-preview', RecordingPreview);
