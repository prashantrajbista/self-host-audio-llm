const STATE_COLORS = {
  idle: "#6b7280",
  listening: "#3b82f6",
  thinking: "#f59e0b",
  speaking: "#22c55e",
};

export class Orb {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.state = "idle";
    this._tick = this._tick.bind(this);
    this._phase = 0;
    requestAnimationFrame(this._tick);
  }

  setState(state) {
    this.state = state;
  }

  _tick() {
    const { ctx, canvas } = this;
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    this._phase += this.state === "idle" ? 0.02 : 0.08;
    const pulse = 1 + 0.08 * Math.sin(this._phase);
    const radius = Math.min(w, h) * 0.25 * pulse;

    ctx.beginPath();
    ctx.arc(w / 2, h / 2, radius, 0, Math.PI * 2);
    ctx.fillStyle = STATE_COLORS[this.state] || STATE_COLORS.idle;
    ctx.fill();

    requestAnimationFrame(this._tick);
  }
}
