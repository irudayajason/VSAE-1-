/**
 * VSAE 3D Golden Sphere — v10 DEFINITIVE IMPLEMENTATION
 * ======================================================
 * Frame-by-frame video analysis results:
 *
 * SPHERE: Large, prominent, entirely golden/amber. NO dark side.
 *   - High emissive so it glows uniformly like a small sun
 *   - Specular highlight on upper-right quadrant
 *   - Surface color REACTS to orbiting colored lights
 *
 * POSITION: Centered horizontally, in the upper ~30% of viewport.
 *   Content (heading, search, cards) pushed to lower 60% via CSS.
 *   Sphere center sits ~65px above the heading text.
 *
 * RINGS: 4 bright luminous orbital energy trails
 *   - Thin bright core line + wider soft glow halo
 *   - Different tilts, speeds, radii
 *   - Golden/amber colored with additive blending
 *
 * GLOW: Multi-layer radial sprites behind sphere
 *   - Tight bright core glow
 *   - Mid-range warm haze
 *   - Extended atmospheric fill
 *
 * SPARKLE: Bright point at bottom of sphere (where light converges)
 *   - Pulsating lens-flare star
 *
 * PARTICLES: 120 golden dust scattered across ENTIRE viewport
 *
 * MOTION: Smooth sine micro-float. NO jumping. NO spring physics.
 *
 * SHADOWS: NONE. Zero. Removed completely.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', initSphere3D);

  function initSphere3D() {
    const canvas = document.getElementById('sphere-canvas');
    if (!canvas) return;
    const welcomeView = document.getElementById('welcome-view');
    if (!welcomeView) return;
    const heading = welcomeView.querySelector('.main-heading');

    function getSize() {
      const rect = welcomeView.getBoundingClientRect();
      return { w: rect.width || window.innerWidth, h: rect.height || window.innerHeight };
    }

    let { w, h } = getSize();
    const dpr = Math.min(window.devicePixelRatio, 2);

    /* ═══ Renderer ═══ */
    const renderer = new THREE.WebGLRenderer({
      canvas, alpha: true, antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(w, h);
    renderer.setPixelRatio(dpr);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    renderer.outputEncoding = THREE.sRGBEncoding;

    /* ═══ Scene & Camera ═══ */
    const scene = new THREE.Scene();
    const FOV = 24;
    const camera = new THREE.PerspectiveCamera(FOV, w / h, 0.1, 200);
    camera.position.set(0, 0, 14);
    camera.lookAt(0, 0, 0);

    /* ═══ Sphere World Y — place in upper portion of view ═══ */
    function getSphereWorldY() {
      const vFov = FOV * Math.PI / 180;
      const halfH = Math.tan(vFov / 2) * camera.position.z;
      // Place sphere center between navbar and heading
      // halfH * 0.55 centers in the gap above content
      return halfH * 0.55;
    }

    let sphereY = getSphereWorldY();

    /* ═══ Procedural golden env cubemap ═══ */
    function buildEnvMap() {
      const sz = 128;
      const faces = [];
      const cfgs = [
        { cx: 0.3, cy: 0.2, b: 0.8 }, { cx: 0.7, cy: 0.3, b: 0.5 },
        { cx: 0.5, cy: 0.1, b: 1.0 }, { cx: 0.5, cy: 0.9, b: 0.15 },
        { cx: 0.4, cy: 0.3, b: 0.65 }, { cx: 0.6, cy: 0.4, b: 0.55 },
      ];
      for (const c of cfgs) {
        const cv = document.createElement('canvas');
        cv.width = sz; cv.height = sz;
        const ctx = cv.getContext('2d');
        const g = ctx.createRadialGradient(sz * c.cx, sz * c.cy, 0, sz * c.cx, sz * c.cy, sz * 0.9);
        g.addColorStop(0, `rgba(255,230,130,${c.b * 0.65})`);
        g.addColorStop(0.25, `rgba(210,170,50,${c.b * 0.35})`);
        g.addColorStop(0.6, `rgba(70,50,10,${c.b * 0.12})`);
        g.addColorStop(1, 'rgba(12,10,6,1)');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, sz, sz);
        // Specular spot
        const h = ctx.createRadialGradient(sz * c.cx, sz * c.cy, 0, sz * c.cx, sz * c.cy, sz * 0.15);
        h.addColorStop(0, `rgba(255,252,230,${c.b * 0.9})`);
        h.addColorStop(1, 'transparent');
        ctx.fillStyle = h;
        ctx.fillRect(0, 0, sz, sz);
        faces.push(new THREE.CanvasTexture(cv));
      }
      const cubeMap = new THREE.CubeTexture(faces.map(f => f.image));
      cubeMap.needsUpdate = true;
      return cubeMap;
    }
    const envMap = buildEnvMap();

    /* ═══════════════════════════════════════════════════════════
       SPHERE — large, fully golden, no dark side
    ═══════════════════════════════════════════════════════════ */
    const SR = 0.6; // compact radius — fits between navbar and heading

    const sphereGeo = new THREE.SphereGeometry(SR, 128, 80);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(0xd4a828),
      metalness: 0.65,
      roughness: 0.28,
      envMap,
      envMapIntensity: 1.8,
      // HIGH emissive = sphere is uniformly bright, no dark side
      emissive: new THREE.Color(0xc89020),
      emissiveIntensity: 0.65,
    });
    const sphere = new THREE.Mesh(sphereGeo, sphereMat);
    sphere.position.set(0, sphereY, 0);
    scene.add(sphere);

    // Store base colors for dynamic tinting
    const baseSphereColor = new THREE.Color(0xd4a828);
    const baseSphereEmissive = new THREE.Color(0xc89020);

    /* ═══════════════════════════════════════════════════════════
       LIGHTING — even from ALL directions, zero shadows
    ═══════════════════════════════════════════════════════════ */
    // Strong ambient fills every surface
    scene.add(new THREE.AmbientLight(0x8a6510, 1.6));

    // Key light from front-top
    const keyLight = new THREE.DirectionalLight(0xffe8a0, 1.6);
    keyLight.position.set(1, sphereY + 4, 6);
    scene.add(keyLight);

    // Back fill — eliminates ANY dark bottom
    const backFill = new THREE.DirectionalLight(0xd4a828, 1.0);
    backFill.position.set(0, sphereY - 3, -5);
    scene.add(backFill);

    // Left fill
    const leftFill = new THREE.DirectionalLight(0xd4a828, 0.6);
    leftFill.position.set(-4, sphereY, 1.5);
    scene.add(leftFill);

    // Right fill
    const rightFill = new THREE.DirectionalLight(0xc8a830, 0.6);
    rightFill.position.set(4, sphereY, 1.5);
    scene.add(rightFill);

    // Bottom uplighter
    const bottomLight = new THREE.PointLight(0xd4a828, 0.5, 6);
    bottomLight.position.set(0, sphereY - 1.8, 2);
    scene.add(bottomLight);

    /* ═══════════════════════════════════════════════════════════
       ORBITING COLORED LIGHTS — dynamically tint the sphere
    ═══════════════════════════════════════════════════════════ */
    const orbitLights = [];
    const lightDefs = [
      { col: 0xff8844, int: 2.0, dist: 5, spd: 0.50, rad: 1.9, yOff: 0,    phase: 0 },
      { col: 0x66bbff, int: 1.4, dist: 5, spd:-0.38, rad: 2.0, yOff: 0.3,  phase: Math.PI * 0.5 },
      { col: 0xffcc22, int: 1.8, dist: 5, spd: 0.28, rad: 1.7, yOff:-0.2,  phase: Math.PI },
      { col: 0xff55bb, int: 1.0, dist: 4, spd:-0.48, rad: 2.1, yOff: 0.15, phase: Math.PI * 1.5 },
    ];

    lightDefs.forEach(d => {
      const light = new THREE.PointLight(d.col, d.int, d.dist);
      light.position.set(d.rad, sphereY, 0);
      scene.add(light);
      orbitLights.push({ light, ...d, color: new THREE.Color(d.col) });
    });

    /* ═══════════════════════════════════════════════════════════
       GLOW — multi-layer volumetric sprites
    ═══════════════════════════════════════════════════════════ */
    function mkGlow(innerCol, outerCol, midCol, opa, scale) {
      const c = document.createElement('canvas');
      c.width = 512; c.height = 512;
      const ctx = c.getContext('2d');
      const g = ctx.createRadialGradient(256, 256, 0, 256, 256, 256);
      g.addColorStop(0, innerCol);
      g.addColorStop(0.1, outerCol);
      g.addColorStop(0.35, midCol);
      g.addColorStop(0.7, 'rgba(180,130,20,0.01)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, 512, 512);
      const mat = new THREE.SpriteMaterial({
        map: new THREE.CanvasTexture(c),
        transparent: true, opacity: opa,
        depthWrite: false, blending: THREE.AdditiveBlending,
      });
      const sp = new THREE.Sprite(mat);
      sp.scale.set(scale, scale, 1);
      sp.renderOrder = -2;
      return { sp, mat };
    }

    // Core: tight bright glow — scaled for compact sphere
    const g1 = mkGlow(
      'rgba(255,230,130,0.45)', 'rgba(220,175,50,0.20)',
      'rgba(200,155,40,0.06)', 0.55, 1.5
    );
    scene.add(g1.sp);

    // Mid haze
    const g2 = mkGlow(
      'rgba(200,160,40,0.1)', 'rgba(200,160,40,0.04)',
      'rgba(180,130,25,0.015)', 0.30, 3.0
    );
    scene.add(g2.sp);

    // Wide atmospheric
    const g3 = mkGlow(
      'rgba(170,130,25,0.04)', 'rgba(170,130,25,0.015)',
      'rgba(150,110,20,0.005)', 0.15, 5.5
    );
    scene.add(g3.sp);

    /* ═══════════════════════════════════════════════════════════
       ORBITAL RINGS — bright luminous energy trails
    ═══════════════════════════════════════════════════════════ */
    const ringDefs = [
      { r: 1.0,  tX: 1.15, tZ: 0.12, spd:  0.32, opa: 0.58, tw: 0.010, gw: 0.05 },
      { r: 1.13, tX: 0.38, tZ: 0.85, spd: -0.24, opa: 0.50, tw: 0.009, gw: 0.04 },
      { r: 1.23, tX: 0.82, tZ: 0.5,  spd:  0.18, opa: 0.42, tw: 0.008, gw: 0.04 },
      { r: 0.9,  tX: 0.15, tZ: 1.25, spd: -0.38, opa: 0.54, tw: 0.010, gw: 0.05 },
    ];

    const rings = ringDefs.map(d => {
      // Core ring (thin bright)
      const coreGeo = new THREE.TorusGeometry(d.r, d.tw, 16, 240);
      const coreMat = new THREE.MeshBasicMaterial({
        color: 0xffd860, transparent: true, opacity: d.opa,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      const core = new THREE.Mesh(coreGeo, coreMat);
      core.rotation.set(d.tX, 0, d.tZ);
      core.position.y = sphereY;
      scene.add(core);

      // Glow ring (wider, softer)
      const glowGeo = new THREE.TorusGeometry(d.r, d.gw, 16, 240);
      const glowMat = new THREE.MeshBasicMaterial({
        color: 0xc89820, transparent: true, opacity: d.opa * 0.18,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      const glow = new THREE.Mesh(glowGeo, glowMat);
      glow.rotation.set(d.tX, 0, d.tZ);
      glow.position.y = sphereY;
      scene.add(glow);

      return { core, coreMat, glow, glowMat, speed: d.spd, baseOpa: d.opa };
    });

    /* Sparkles removed per user request */

    /* ═══════════════════════════════════════════════════════════
       SCREEN-WIDE PARTICLES — golden dust/stars
    ═══════════════════════════════════════════════════════════ */
    const PC = 120;
    const pPos = new Float32Array(PC * 3);
    const pVel = [];

    const vFov = FOV * Math.PI / 180;
    const visH = Math.tan(vFov / 2) * camera.position.z * 2;
    const visW = visH * (w / h);

    for (let i = 0; i < PC; i++) {
      pPos[i * 3]     = (Math.random() - 0.5) * visW * 1.3;
      pPos[i * 3 + 1] = (Math.random() - 0.5) * visH * 1.3;
      pPos[i * 3 + 2] = (Math.random() - 0.5) * 8;
      pVel.push({
        dx: (Math.random() - 0.5) * 0.002,
        dy: (Math.random() - 0.5) * 0.0015,
        phase: Math.random() * Math.PI * 2,
      });
    }

    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));

    // Dot texture
    const dotC = document.createElement('canvas');
    dotC.width = 64; dotC.height = 64;
    const dCtx = dotC.getContext('2d');
    const dG = dCtx.createRadialGradient(32, 32, 0, 32, 32, 32);
    dG.addColorStop(0, 'rgba(255,248,210,1)');
    dG.addColorStop(0.12, 'rgba(255,228,140,0.9)');
    dG.addColorStop(0.35, 'rgba(200,168,48,0.3)');
    dG.addColorStop(1, 'rgba(200,168,48,0)');
    dCtx.fillStyle = dG;
    dCtx.fillRect(0, 0, 64, 64);

    const pMat = new THREE.PointsMaterial({
      map: new THREE.CanvasTexture(dotC),
      size: 0.09, transparent: true, opacity: 0.4,
      depthWrite: false, blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    });
    const particles = new THREE.Points(pGeo, pMat);
    scene.add(particles);

    /* ═══════════════════════════════════════════════════════════
       ANIMATION LOOP — smooth, NO jumping
    ═══════════════════════════════════════════════════════════ */
    const clock = new THREE.Clock();
    let animId;
    const SY = sphereY;
    const tintColor = new THREE.Color();

    function animate() {
      animId = requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);
      const t = clock.getElapsedTime();

      // Gentle micro-float
      const floatY = SY + Math.sin(t * 0.4) * 0.04;
      const swayX = Math.sin(t * 0.25) * 0.018;
      const swayZ = Math.cos(t * 0.18) * 0.008;

      /* ── Sphere position & rotation ── */
      sphere.position.set(swayX, floatY, swayZ);
      sphere.rotation.y += 0.003;
      sphere.rotation.x = Math.sin(t * 0.1) * 0.012;

      /* ── Orbiting colored lights — tint sphere surface ── */
      tintColor.set(0, 0, 0);
      let totalWeight = 0;

      orbitLights.forEach(ol => {
        const a = t * ol.spd + ol.phase;
        const lx = swayX + Math.cos(a) * ol.rad;
        const ly = floatY + ol.yOff + Math.sin(a * 0.6) * 0.25;
        const lz = Math.sin(a) * ol.rad;
        ol.light.position.set(lx, ly, lz);

        // Pulse intensity
        const pulse = 0.82 + Math.sin(t * 1.4 + ol.phase) * 0.18;
        ol.light.intensity = ol.int * pulse;

        // Calculate proximity weight for color blending
        const dx = lx - swayX;
        const dy = ly - floatY;
        const dz = lz - swayZ;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        const weight = Math.max(0, 1.0 - dist / (ol.rad * 1.5)) * pulse;
        tintColor.r += ol.color.r * weight;
        tintColor.g += ol.color.g * weight;
        tintColor.b += ol.color.b * weight;
        totalWeight += weight;
      });

      // Blend orbiting light colors into sphere material
      if (totalWeight > 0.01) {
        tintColor.multiplyScalar(1.0 / totalWeight);
        const blend = 0.15; // 15% color influence from orbiting lights
        sphereMat.color.copy(baseSphereColor).lerp(tintColor, blend);
        sphereMat.emissive.copy(baseSphereEmissive).lerp(tintColor, blend * 0.6);
      }

      /* ── Rings ── */
      rings.forEach(r => {
        r.core.rotation.y += r.speed * dt;
        r.core.position.set(swayX, floatY, swayZ);
        r.glow.rotation.y = r.core.rotation.y;
        r.glow.position.set(swayX, floatY, swayZ);
        const pulse = 0.86 + Math.sin(t * 1.2 + r.core.rotation.z * 2) * 0.14;
        r.coreMat.opacity = r.baseOpa * pulse;
        r.glowMat.opacity = r.baseOpa * 0.18 * pulse;
      });

      /* ── Glow follows sphere ── */
      [g1, g2, g3].forEach(g => g.sp.position.set(swayX, floatY, swayZ - 0.6));
      const gP = 1.0 + Math.sin(t * 0.5) * 0.03;
      g1.sp.scale.set(1.5 * gP, 1.5 * gP, 1);
      g1.mat.opacity = 0.5 + Math.sin(t * 0.85) * 0.05;
      g2.sp.scale.set(3.0 * gP, 3.0 * gP, 1);
      g3.sp.scale.set(5.5 * gP, 5.5 * gP, 1);

      /* ── Particles ── */
      const posArr = pGeo.attributes.position.array;
      const hW = visW * 0.65;
      const hH = visH * 0.65;
      for (let i = 0; i < PC; i++) {
        const v = pVel[i];
        const idx = i * 3;
        posArr[idx] += v.dx;
        posArr[idx + 1] += v.dy;
        if (posArr[idx] > hW) posArr[idx] = -hW;
        if (posArr[idx] < -hW) posArr[idx] = hW;
        if (posArr[idx + 1] > hH) posArr[idx + 1] = -hH;
        if (posArr[idx + 1] < -hH) posArr[idx + 1] = hH;
      }
      pGeo.attributes.position.needsUpdate = true;
      pMat.opacity = 0.3 + Math.sin(t * 1.6) * 0.06;

      renderer.render(scene, camera);
    }

    animate();

    /* ═══ Resize ═══ */
    function onResize() {
      const s = getSize();
      w = s.w; h = s.h;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      sphereY = getSphereWorldY();
    }
    window.addEventListener('resize', onResize);

    /* ═══ Pause/resume on view switch ═══ */
    const obs = new MutationObserver(() => {
      if (welcomeView.classList.contains('hidden')) {
        cancelAnimationFrame(animId);
      } else {
        clock.start();
        animate();
      }
    });
    obs.observe(welcomeView, { attributes: true, attributeFilter: ['class'] });
  }
})();
