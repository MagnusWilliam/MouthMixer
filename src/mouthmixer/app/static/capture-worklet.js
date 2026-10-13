"use strict";
// Mic capture on the audio thread. The page's main thread can be busy (drawing the pitch lane, loading
// loops), and the old ScriptProcessor capture lost audio whenever it was; an AudioWorklet runs with the
// audio itself and doesn't. Every 2048 samples it posts the block with the context time of its first
// sample, so the page can put each block exactly where it belongs (and spot any gap).
class MMCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.size = 2048;
    this.buf = new Float32Array(this.size);
    this.n = 0;
    this.t0 = 0;
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) {  // no mic audio this moment (e.g. while the mic starts): start a fresh block when it returns
      this.n = 0;
      return true;
    }
    let i = 0;
    while (i < ch.length) {
      if (this.n === 0) this.t0 = currentTime + i / sampleRate;
      const k = Math.min(ch.length - i, this.size - this.n);
      this.buf.set(ch.subarray(i, i + k), this.n);
      this.n += k; i += k;
      if (this.n === this.size) {
        this.port.postMessage({ t: this.t0, d: this.buf }, [this.buf.buffer]);
        this.buf = new Float32Array(this.size);
        this.n = 0;
      }
    }
    return true;
  }
}
registerProcessor("mm-capture", MMCapture);
