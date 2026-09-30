export async function startMic(
  onFrame: (pcm16: ArrayBuffer) => void,
): Promise<{ ctx: AudioContext; stream: MediaStream; analyser: AnalyserNode }> {
  const ctx = new AudioContext({ sampleRate: 16000 });
  await ctx.audioWorklet.addModule("/worklet/recorder-worklet.js");
  const stream = await navigator.mediaDevices.getUserMedia({
    // NS on: background noise hurts Whisper more than the occasional gated quiet syllable. AGC lifts distant
    // speech; AEC keeps the assistant's own playback from being picked up as the user.
    audio: { channelCount: 1, noiseSuppression: true, autoGainControl: true, echoCancellation: true },
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

// ponytail: schedule-ahead queue with a fixed 60ms start lead (the server paces sends) —
// add an adaptive jitter buffer if playback stutters under real network conditions.
const JITTER_S = 0.06;

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
    const int16 = new Int16Array(arrayBuffer, 0, arrayBuffer.byteLength >> 1); // ignore a stray odd byte
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;

    const buf = this.ctx.createBuffer(1, float32.length, this.ctx.sampleRate);
    buf.copyToChannel(float32, 0);

    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.analyser);
    this.sources.add(src);
    src.onended = () => this.sources.delete(src);

    // queue ran dry (or first chunk): start a little ahead so a slightly late next chunk doesn't underrun
    const now = this.ctx.currentTime;
    const startAt = this.nextTime > now ? this.nextTime : now + JITTER_S;
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

  // Both sides of the call mixed into one stream (for MediaRecorder): the reply audio as played here,
  // plus the mic. Mixed in this context so they share one clock.
  mixWith(mic: MediaStream): MediaStream {
    const dest = this.ctx.createMediaStreamDestination();
    this.analyser.connect(dest);
    this.ctx.createMediaStreamSource(mic).connect(dest);
    return dest.stream;
  }

  close(): void {
    void this.ctx.close();
  }
}

// Records a stream; `stop` resolves with the audio once the recorder has flushed.
export function startRecording(stream: MediaStream): { stop: () => Promise<Blob> } {
  const mimeType = ["audio/webm;codecs=opus", "audio/mp4"].find((t) => MediaRecorder.isTypeSupported(t));
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  const done = new Promise<Blob>((resolve) => {
    recorder.onstop = () => resolve(new Blob(chunks, { type: recorder.mimeType }));
  });
  recorder.start(1000); // timesliced: chunks already collected survive an abrupt teardown
  return {
    stop: () => {
      if (recorder.state !== "inactive") recorder.stop();
      return done;
    },
  };
}
