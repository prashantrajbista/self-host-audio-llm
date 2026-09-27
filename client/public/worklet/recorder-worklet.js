const FRAME_SAMPLES = 320; // 20ms @ 16kHz

class RecorderWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(0);
  }

  process(inputs) {
    const input = inputs[0][0];
    if (!input) return true;

    const combined = new Float32Array(this.buffer.length + input.length);
    combined.set(this.buffer);
    combined.set(input, this.buffer.length);

    let offset = 0;
    while (combined.length - offset >= FRAME_SAMPLES) {
      const frame = combined.subarray(offset, offset + FRAME_SAMPLES);
      const pcm16 = new Int16Array(FRAME_SAMPLES);
      for (let i = 0; i < FRAME_SAMPLES; i++) {
        const s = Math.max(-1, Math.min(1, frame[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
      offset += FRAME_SAMPLES;
    }
    this.buffer = combined.subarray(offset);
    return true;
  }
}

registerProcessor("recorder-worklet", RecorderWorklet);
