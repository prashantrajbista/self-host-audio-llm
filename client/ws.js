import { startMic, Player } from "./audio.js";
import { Orb } from "./orb.js";

const orb = new Orb(document.getElementById("orb"));
const transcriptEl = document.getElementById("transcript");
const player = new Player(24000);
let socket = null;

async function connect() {
  const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${wsProtocol}//${location.host}/ws`);
  socket.binaryType = "arraybuffer";

  socket.onmessage = (event) => {
    if (typeof event.data === "string") {
      const msg = JSON.parse(event.data);
      if (msg.type === "state") orb.setState(msg.data);
      if (msg.type === "partial_transcript") transcriptEl.textContent = msg.data;
      if (msg.type === "token") transcriptEl.textContent += msg.data;
      if (msg.type === "interrupt") player.stopAll();
    } else {
      player.playChunk(event.data);
    }
  };

  socket.onopen = async () => {
    await startMic((pcm16Buffer) => {
      if (socket.readyState === WebSocket.OPEN) socket.send(pcm16Buffer);
    });
  };
}

document.getElementById("connect").addEventListener("click", connect);
