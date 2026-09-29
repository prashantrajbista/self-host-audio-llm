export async function startMic(
  onFrame: (pcm16: ArrayBuffer) => void,
): Promise<{ ctx: AudioContext; stream: MediaStream; analyser: AnalyserNode }> {
  const ctx = new AudioContext({ sampleRate: 16000 });
  await ctx.audioWorklet.addModule("/worklet/recorder-worklet.js");
  const stream = await navigator.mediaDevices.getUserMedia({
    // NS off: it gates quiet speech, which Whisper then mishears. AGC lifts distant speech; AEC stays on
    // so the assistant's own playback isn't picked up as the user.
    audio: { channelCount: 1, noiseSuppression: false, autoGainControl: true, echoCancellation: true },
  });
  const source = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, "recorder-worklet");
  node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => onFrame(e.data);
  source.connect(node);
  const analyser = ctx.createAnalyser();
  source.connect(analyser);
  return { ctx, stream, analyser };
}

// RMS loudness of whatever is flowing through the analyser, mapped to roughly 0..1 for speech.
const levelBuf = new Float32Array(2048);
export function audioLevel(analyser: AnalyserNode | null): number {
  if (!analyser) return 0;
  const buf = levelBuf.subarray(0, analyser.fftSize);
  analyser.getFloatTimeDomainData(buf);
  let sum = 0;
  for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
  return Math.min(1, Math.sqrt(sum / buf.length) * 6);
}

// ponytail: fixed schedule-ahead queue, no jitter buffer/backpressure handling —
// add if playback stutters under real network conditions.
export class Player {
  private ctx: AudioContext;
  private nextTime: number;
  private sources = new Set<AudioBufferSourceNode>();
  readonly analyser: AnalyserNode;

  constructor(sampleRate = 24000) {
    this.ctx = new AudioContext({ sampleRate });
    this.nextTime = 0;
    this.analyser = this.ctx.createAnalyser();
    this.analyser.connect(this.ctx.destination);
  }

  playChunk(arrayBuffer: ArrayBuffer): void {
    const int16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;

    const buf = this.ctx.createBuffer(1, float32.length, this.ctx.sampleRate);
    buf.copyToChannel(float32, 0);

    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.analyser);
    this.sources.add(src);
    src.onended = () => this.sources.delete(src);

    const startAt = Math.max(this.ctx.currentTime, this.nextTime);
    src.start(startAt);
    this.nextTime = startAt + buf.duration;
  }

  // Stop what's already scheduled, not just future chunks — otherwise queued audio keeps playing
  // for seconds after an interrupt.
  stopAll(): void {
    this.sources.forEach((src) => src.stop());
    this.sources.clear();
    this.nextTime = this.ctx.currentTime;
  }

  close(): void {
    void this.ctx.close();
  }
}
