export async function startMic(
  onFrame: (pcm16: ArrayBuffer) => void,
): Promise<{ ctx: AudioContext; stream: MediaStream }> {
  const ctx = new AudioContext({ sampleRate: 16000 });
  await ctx.audioWorklet.addModule("/worklet/recorder-worklet.js");
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1 },
  });
  const source = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, "recorder-worklet");
  node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => onFrame(e.data);
  source.connect(node);
  return { ctx, stream };
}

// ponytail: fixed schedule-ahead queue, no jitter buffer/backpressure handling —
// add if playback stutters under real network conditions.
export class Player {
  private ctx: AudioContext;
  private nextTime: number;

  constructor(sampleRate = 24000) {
    this.ctx = new AudioContext({ sampleRate });
    this.nextTime = 0;
  }

  playChunk(arrayBuffer: ArrayBuffer): void {
    const int16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;

    const buf = this.ctx.createBuffer(1, float32.length, this.ctx.sampleRate);
    buf.copyToChannel(float32, 0);

    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.ctx.destination);

    const startAt = Math.max(this.ctx.currentTime, this.nextTime);
    src.start(startAt);
    this.nextTime = startAt + buf.duration;
  }

  stopAll(): void {
    this.nextTime = this.ctx.currentTime;
  }
}
