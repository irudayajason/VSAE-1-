/* ═══════════════════════════════════════════════════════════════════
   DUSTFX — Ambient golden dust drifting like wind
   Renders behind ALL content (z-index: -1)
   Particles spawn at the left, drift right, and fade near the edge.
═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const canvas = document.getElementById('dust-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  /* ── Config ── */
  const PARTICLE_COUNT = 90;
  const WIND_MIN = 0.25;          // min horizontal speed (px/frame)
  const WIND_MAX = 0.70;          // max horizontal speed
  const DRIFT_Y = 0.12;           // vertical wander amplitude
  const BASE_OPACITY_MIN = 0.15;
  const BASE_OPACITY_MAX = 0.50;
  const SIZE_MIN = 1.0;
  const SIZE_MAX = 2.8;
  const GLOW_RADIUS = 8;          // soft radial glow around each dot

  /* ── Golden palette — warm tones ── */
  const COLORS = [
    { r: 255, g: 215, b: 80 },    // bright gold
    { r: 240, g: 195, b: 60 },    // warm gold
    { r: 255, g: 230, b: 130 },   // pale gold
    { r: 220, g: 175, b: 50 },    // deep gold
    { r: 255, g: 200, b: 90 },    // sunset gold
    { r: 200, g: 160, b: 40 },    // antique gold
  ];

  let W, H;
  const particles = [];

  /* ── Resize ── */
  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  /* ── Helpers ── */
  function rand(a, b) { return a + Math.random() * (b - a); }
  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

  /* ── Particle factory ── */
  function createParticle(fromLeft) {
    const color = pick(COLORS);
    return {
      // Spawn along left edge (or random x on init)
      x: fromLeft ? rand(-30, -5) : rand(-30, W * 0.6),
      y: rand(0, H),
      vx: rand(WIND_MIN, WIND_MAX),
      vy: 0,
      size: rand(SIZE_MIN, SIZE_MAX),
      baseAlpha: rand(BASE_OPACITY_MIN, BASE_OPACITY_MAX),
      alpha: 0,
      r: color.r,
      g: color.g,
      b: color.b,
      // Wobble
      wobbleAmp: rand(0.3, 1.2),
      wobbleFreq: rand(0.008, 0.025),
      wobblePhase: rand(0, Math.PI * 2),
      // Twinkle
      twinkleSpeed: rand(0.01, 0.04),
      twinklePhase: rand(0, Math.PI * 2),
      age: 0,
    };
  }

  /* ── Init ── */
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(createParticle(false));
  }

  /* ── Draw a single glowing dot ── */
  function drawDot(p) {
    if (p.alpha < 0.005) return;

    ctx.save();

    // Outer glow
    const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, GLOW_RADIUS * p.size);
    grad.addColorStop(0, `rgba(${p.r},${p.g},${p.b},${p.alpha * 0.6})`);
    grad.addColorStop(0.3, `rgba(${p.r},${p.g},${p.b},${p.alpha * 0.2})`);
    grad.addColorStop(1, `rgba(${p.r},${p.g},${p.b},0)`);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(p.x, p.y, GLOW_RADIUS * p.size, 0, Math.PI * 2);
    ctx.fill();

    // Bright core
    ctx.globalAlpha = p.alpha;
    ctx.fillStyle = `rgb(${p.r},${p.g},${p.b})`;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size * 0.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  /* ── Animation loop ── */
  function animate() {
    requestAnimationFrame(animate);
    ctx.clearRect(0, 0, W, H);

    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.age++;

      // ── Movement ──
      p.x += p.vx;
      p.y += Math.sin(p.age * p.wobbleFreq + p.wobblePhase) * p.wobbleAmp * DRIFT_Y;

      // ── Fade logic ──
      // Fraction of journey across screen (0 = left edge, 1 = right edge)
      const progress = Math.max(0, p.x / W);

      // Fade in for first 5% of screen, fade out for last 35%
      let fadeMul = 1;
      if (progress < 0.05) {
        fadeMul = progress / 0.05;                     // gentle fade-in
      } else if (progress > 0.65) {
        fadeMul = 1 - (progress - 0.65) / 0.35;        // gradual fade-out
      }
      fadeMul = Math.max(0, Math.min(1, fadeMul));

      // Twinkle
      const twinkle = 0.7 + 0.3 * Math.sin(p.age * p.twinkleSpeed + p.twinklePhase);

      p.alpha = p.baseAlpha * fadeMul * twinkle;

      // ── Draw ──
      drawDot(p);

      // ── Respawn when off-screen or fully faded ──
      if (p.x > W + 20 || (progress > 0.95 && p.alpha < 0.01)) {
        particles[i] = createParticle(true);
      }
    }
  }

  animate();
})();
