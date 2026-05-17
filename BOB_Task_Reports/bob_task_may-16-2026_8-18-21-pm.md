**User:**

<task>
remove the bridgefy file and evac file from the repo and push it to git again
</task>
<environment_details>
# VSCode Visible Files
../Downloads/bob_task_may-16-2026_8-08-48-pm.md

# VSCode Open Tabs
scripts/validate_compliance_report.py,reports/sample_report.json,../Downloads/bob_task_may-16-2026_8-08-48-pm.md,.github/workflows/vsae-gate.yml

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T14:47:44.942Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.00

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>


# Current Workspace Directory (/Users/jason/vsae) Files
.gitignore
Bridgefy_Final_Project_Document.md.resolved
Evac_Final_Project_Document.md
LICENSE
Literature.md
README.md
test_mps.py
xxx
.github/
backend/
backend/__init__.py
backend/ablation.py
backend/embedding.py
backend/evaluate.py
backend/literature_notes.md
backend/locator.py
backend/main.py
frontend/
frontend/app.js
frontend/dustfx.js
frontend/index.html
frontend/sphere3d.js
frontend/style.css
reports/
reports/sample_report.json
scripts/
scripts/validate_compliance_report.py
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

I'll help you remove the Bridgefy and Evac files from the repository and push the changes to git. Let me start by identifying these files and then removing them.

<read_file>
<args>
  <file>
    <path>Bridgefy_Final_Project_Document.md.resolved</path>
  </file>
  <file>
    <path>Evac_Final_Project_Document.md</path>
  </file>
</args>
</read_file>

---

**User:**

[read_file for 'Bridgefy_Final_Project_Document.md.resolved', 'Evac_Final_Project_Document.md'] Result:
<files>
<file><path>Bridgefy_Final_Project_Document.md.resolved</path>
<content lines="1-415">
  1 | # BRIDGEFY — OFFLINE DISASTER COORDINATION NETWORK
  2 | 
  3 | ## Final Project Document
  4 | 
  5 | > **When everything fails, Bridgefy doesn't.**
  6 | 
  7 | > [!CAUTION]
  8 | > **Name Conflict:** "Bridgefy" is an existing mesh-messaging company ([bridgefy.me](https://bridgefy.me)). **Strongly consider renaming** before presenting to judges — alternatives: **ResQLink**, **GridPulse**, **SafeSignal**, **MeshAlert**.
  9 | 
 10 | ---
 11 | 
 12 | ## 1. Elevator Pitch
 13 | 
 14 | Bridgefy is an Android app that turns every phone into a node in an invisible emergency network. When cell towers and internet are destroyed, victims send distress signals, rescue teams coordinate response, and officials broadcast verified alerts — **all without internet**. Messages hop silently phone-to-phone through human movement. A Gateway at the disaster's edge bridges the mesh to a cloud dashboard accessible worldwide. People without the app connect through a Wi-Fi portal — **no download needed**.
 15 | 
 16 | ---
 17 | 
 18 | ## 2. Architecture — Three Zones
 19 | 
 20 | ```
 21 | ┌──────────────────────────────────────────────────────────────────┐
 22 | │  ZONE A — DISASTER ZONE  (No Internet)                           │
 23 | │                                                                  │
 24 | │  📱 Citizen ◄──BLE/WiFi──► 📱 Citizen ◄──BLE/WiFi──► 📱 Field  │
 25 | │       │                         │                   Responder    │
 26 | │       │                         │                       │        │
 27 | │       └─────── BLE/WiFi ────────┘                  BLE/WiFi      │
 28 | │                                                         │        │
 29 | │                  📱 Legacy Phone ──WiFi──► 📶 Captive Portal     │
 30 | └──────────────────────────────────────────────────────────────────┘
 31 |                                                          │
 32 |                                               Satellite / LoRa /
 33 |                                               4G / SMS
 34 |                                                          │
 35 | ┌──────────────────────────────────────────────────────────────────┐
 36 | │  ZONE C — THE BRIDGE  (Edge of Disaster)                         │
 37 | │  📡 Gateway Node (phone with internet connection)                │
 38 | │  Uploads mesh data → Cloud  |  Downloads bulletins → Mesh        │
 39 | └──────────────────────────────────────────────────────────────────┘
 40 |                                                          │
 41 |                                                      Internet
 42 |                                                          │
 43 | ┌──────────────────────────────────────────────────────────────────┐
 44 | │  ZONE B — COMMAND CENTER  (Remote, Has Internet)                 │
 45 | │  🖥️ Web Dashboard: Live SOS map, verified bulletins, ACKs       │
 46 | │  🗄️ Firebase Firestore: Persistent data + real-time sync        │
 47 | └──────────────────────────────────────────────────────────────────┘
 48 | ```
 49 | 
 50 | ---
 51 | 
 52 | ## 3. Five Node Types
 53 | 
 54 | | Node | Activation | Capabilities |
 55 | |---|---|---|
 56 | | **Citizen** | Default on install | 4-button SOS, Volume SOS, Dead Man's Switch, receive bulletins, receive ACKs |
 57 | | **Field Responder** | PIN-gated (production: Ed25519 keypair) | All Citizen abilities **+** offline map with SOS pins, mark "En Route" / "Resolved", activate Captive Portal |
 58 | | **Gateway** | Auto-activates when internet detected | Mesh participant **+** batches all data → Firebase, injects bulletins back into mesh |
 59 | | **Legacy Portal User** | No app needed | Connects to hotspot `EMERGENCY_CONNECT_HERE`, uses browser-based web portal to read bulletins + submit SOS |
 60 | | **Command Center** | Web dashboard (separate) | Live map with color-coded SOSes, issue signed bulletins, send signed ACKs to victims |
 61 | 
 62 | ---
 63 | 
 64 | ## 4. Seven Core Features
 65 | 
 66 | ### 🔴 Feature 1: Four-Button SOS Interface
 67 | 
 68 | | Button | Status Code | Color |
 69 | |---|---|---|
 70 | | MEDICAL | `0x01` | Red |
 71 | | TRAPPED | `0x02` | Orange |
 72 | | HAZARD | `0x03` | Yellow |
 73 | | SAFE | `0x04` | Green |
 74 | 
 75 | - One tap sends SOS with **automatic GPS** — no typing under stress
 76 | - Optional 100-char text note for details
 77 | - Rate-limited: **1 SOS per 2 minutes** per device (hardware fingerprinted)
 78 | 
 79 | ---
 80 | 
 81 | ### 📳 Feature 2: Volume SOS
 82 | 
 83 | - Press **Volume Down 3× fast** = instant distress signal
 84 | - Works with **screen off**, in the dark, in your pocket
 85 | - **Haptic pulse** confirmation only (silent — critical for stealth in dangerous situations)
 86 | - Sends with last known GPS + `TRAPPED` status by default
 87 | 
 88 | ---
 89 | 
 90 | ### ⏰ Feature 3: Dead Man's Switch
 91 | 
 92 | - If the user doesn't interact with their phone for **45 minutes**, the app auto-broadcasts a **welfare-check beacon**
 93 | - Catches **unconscious or incapacitated** victims
 94 | - Appears as **amber alert** on responder maps (distinct from active SOS)
 95 | - Runs via Android `ForegroundService` with persistent notification
 96 | 
 97 | > [!WARNING]
 98 | > **Android gotcha:** OEMs like Xiaomi, Samsung, and Huawei aggressively kill background/foreground services. Test on actual demo phones. May need battery optimization exemption.
 99 | 
100 | ---
101 | 
102 | ### 📡 Feature 4: Offline Mesh Network
103 | 
104 | ```
105 | Phone A                              Phone B
106 |    │                                    │
107 |    ├── BLE Advertise (custom UUID) ────►│
108 |    │◄── BLE Discover ──────────────────┤
109 |    │                                    │
110 |    ├── Upgrade to Wi-Fi Direct ────────►│
111 |    │                                    │
112 |    ├── Bloom Filter exchange (~1KB) ───►│  (what I've seen)
113 |    │◄── Bloom Filter exchange ─────────┤  (what you've seen)
114 |    │                                    │
115 |    │   Delta transfer: CRITICAL first,  │
116 |    │   then HIGH → NORMAL → LOW         │
117 |    │                                    │
118 |    ├── Verify HMAC integrity ──────────►│
119 |    │◄── Verify HMAC integrity ─────────┤
120 |    │                                    │
121 |    └── Disconnect. Total: <3 seconds ──►│
122 | ```
123 | 
124 | - **BLE** for discovery (low power)
125 | - **Wi-Fi Direct** for high-speed data transfer
126 | - Messages hop automatically — no user action needed
127 | - Max **10 hops** per message (prevents flooding)
128 | - **TTL: 24 hours** default (stale messages auto-purged)
129 | 
130 | > [!TIP]
131 | > **Hackathon shortcut:** If Bloom filters take too long to implement, fall back to simple **ID-list exchange** (send list of message IDs → partner sends missing ones). Mention Bloom filters as "designed for production."
132 | 
133 | ---
134 | 
135 | ### 🌉 Feature 5: Gateway Bridge
136 | 
137 | - Any phone with internet connection **auto-activates** as a Gateway
138 | - **Inbound:** Batches all mesh data every 5 minutes → uploads to Firebase Firestore
139 | - **Outbound:** Pulls new bulletins/ACKs from Firebase → injects into mesh
140 | - Multiple gateways can operate simultaneously; Firebase deduplicates via unique message IDs
141 | - If gateway goes down, mesh continues independently; syncs backlog on recovery
142 | 
143 | ---
144 | 
145 | ### 📶 Feature 6: Captive Portal (Legacy Device Support)
146 | 
147 | - Any Field Responder can activate a Wi-Fi hotspot named `EMERGENCY_CONNECT_HERE`
148 | - Uses **NanoHTTPD** (embedded HTTP server) to serve a simple HTML page
149 | - ₹500 button phones, iPhones, laptops — anything with Wi-Fi + a browser works
150 | - Portal provides: read bulletins + submit SOS (name, location, status)
151 | - **Zero app download required**
152 | 
153 | > [!NOTE]
154 | > Captive portal auto-redirect behavior varies by device. Have a fallback: instruct users to open browser and navigate to `192.168.49.1`.
155 | 
156 | ---
157 | 
158 | ### 🖥️ Feature 7: Command Center Dashboard
159 | 
160 | - **Web app** (HTML/JS + Leaflet.js) hosted on Firebase Hosting
161 | - **Live map** with color-coded SOS pins (Red=Medical, Orange=Trapped, Yellow=Hazard, Green=Safe, Amber=Dead Man's Switch)
162 | - **Issue bulletins** — typed into a form, cryptographically signed with Ed25519, pushed to Firebase → Gateway → Mesh
163 | - **Send ACKs** — click an SOS pin → type response (e.g., *"Help dispatched, ETA 30 min"*) → signed and sent back to victim's phone
164 | - **Priority sidebar** — ranks zones by threat density
165 | 
166 | ---
167 | 
168 | ## 5. Message Protocol
169 | 
170 | ### SOS Payload — 26 bytes core
171 | 
172 | | Field | Size | Description |
173 | |---|---|---|
174 | | `device_id` | 4B | `sha256(android_id + BLE_MAC)` truncated |
175 | | `latitude` | 4B | Float32 |
176 | | `longitude` | 4B | Float32 |
177 | | `status_code` | 1B | `0x01`=Medical, `0x02`=Trapped, `0x03`=Hazard, `0x04`=Safe, `0x05`=DeadManSwitch |
178 | | `lamport_clock` | 4B | Logical timestamp for ordering |
179 | | `ttl_hours` | 1B | Time-to-live (default 24) |
180 | | `hop_count` | 1B | Incremented each relay, max 10 |
181 | | `max_hops` | 1B | Hard limit |
182 | | `hmac` | 4B | Integrity check (truncated HMAC-SHA256) |
183 | | `flags` | 1B | Volume SOS, Dead Man's Switch, etc. |
184 | | `reserved` | 1B | Future use |
185 | | `text_note` | 0–100B | Optional free-text (UTF-8) |
186 | 
187 | ### Bulletin Payload
188 | 
189 | | Field | Description |
190 | |---|---|
191 | | `alert_type` | Flood / Earthquake / Cyclone / General |
192 | | `affected_zone` | Lat, Lng, Radius (km) |
193 | | `message_text` | Up to 500 chars |
194 | | `ed25519_signature` | 64B — proves it came from Command Center |
195 | | `lamport_clock` | Logical timestamp |
196 | 
197 | ### ACK Payload
198 | 
199 | | Field | Description |
200 | |---|---|
201 | | `target_device_id` | Which victim this ACK is for |
202 | | `response_text` | *"Help dispatched, ETA 30 min"* |
203 | | `ed25519_signature` | 64B — proves authenticity |
204 | 
205 | ---
206 | 
207 | ## 6. Security Model
208 | 
209 | | Threat | Mitigation |
210 | |---|---|
211 | | Fake SOS spam | Hardware fingerprint rate limit: **1 SOS per 2 min**. Field Responders can **mute** a device. |
212 | | Fake bulletins / ACKs | **Ed25519 signature** verification. Public key embedded in app. Private key only on Command Center. |
213 | | Message tampering | **HMAC** integrity check per message. Shared key hardcoded in app (hackathon scope). |
214 | | Stale information | **TTL** field — expired messages purged on every sync. |
215 | | Network flooding | **Max hop count** (10). Messages beyond limit dropped. |
216 | | Replay attacks | **Lamport clock** ordering — reject messages with lower clock than last seen from same device. |
217 | | GPS spoofing | Cross-validate GPS against relay chain geography — flag suspicious locations. |
218 | 
219 | > [!NOTE]
220 | > **Hackathon vs. Production:** The HMAC shared key is hardcoded for the hackathon. In production, this would use per-device keys provisioned during registration, or switch to asymmetric signing.
221 | 
222 | ---
223 | 
224 | ## 7. Power Management
225 | 
226 | | Mode | Trigger | BLE Scan | GPS | Screen | Battery Life |
227 | |---|---|---|---|---|---|
228 | | **Normal** | Default | Every 30s | Every 60s | On | ~8 hrs |
229 | | **Power Saver** | Battery ≤ 30% | Every 5 min | Every 5 min | Dim | ~18 hrs |
230 | | **Emergency Beacon** | Battery ≤ 15% | Minimal broadcast | Off (uses last known) | Off | ~6–8 hrs |
231 | 
232 | ---
233 | 
234 | ## 8. Tech Stack
235 | 
236 | | Component | Technology | Cost |
237 | |---|---|---|
238 | | Mobile App | Android Native (Kotlin) | Free |
239 | | Mesh Discovery | BLE (Android SDK) | Free |
240 | | Mesh Transfer | Nearby Connections API | Free |
241 | | Local Database | Room (SQLite) | Free |
242 | | Captive Portal | NanoHTTPD | Free |
243 | | Offline Maps | OSMDroid + `.mbtiles` | Free |
244 | | Crypto | TweetNaCl-java (Ed25519) | Free |
245 | | Cloud Backend | Firebase Firestore (free tier) | Free |
246 | | Dashboard | HTML/JS + Leaflet.js | Free |
247 | | Dashboard Hosting | Firebase Hosting (free tier) | Free |
248 | | **Total** | | **₹0** |
249 | 
250 | > [!WARNING]
251 | > **Firebase free tier limits:** 50K reads/day, 20K writes/day. Fine for demo. Mention *"production would use dedicated cloud"* if judges ask.
252 | 
253 | ---
254 | 
255 | ## 9. 19-Hour Build Plan (4 People)
256 | 
257 | **Start:** 7:49 PM  |  **Deadline:** Tomorrow 3:00 PM
258 | 
259 | ### Person 1 — Mesh Networking 🔴 (Critical Path)
260 | 
261 | | Hours | Task |
262 | |---|---|
263 | | 0–3 | Nearby Connections API "hello world" — text between 2 phones |
264 | | 3–8 | Store-and-forward relay: msg created on Phone A → relayed via Phone B → arrives at Phone C |
265 | | 8–12 | BLE discovery layer (continuous background scanning) |
266 | | 12–16 | Sync protocol: exchange message ID lists → transfer missing messages, CRITICAL priority first |
267 | | 16–19 | Gateway logic: upload batch to Firebase + pull bulletins from Firebase into mesh |
268 | 
269 | > [!CAUTION]
270 | > **If mesh isn't working by Hour 5**, pivot to simulated mesh (phones on same local Wi-Fi exchanging messages). Show real BLE architecture in slides.
271 | 
272 | ### Person 2 — Mobile App UI
273 | 
274 | | Hours | Task |
275 | |---|---|
276 | | 0–4 | App scaffold: `ForegroundService`, Room DB schema, device fingerprint generation, 3-tab navigation |
277 | | 4–8 | Citizen UI: 4-button SOS interface, GPS grab, payload creation + save to Room |
278 | | 8–12 | Volume SOS: 3× Volume Down detection in `ForegroundService`, haptic confirmation |
279 | | 12–16 | Field Responder mode: PIN gate, OSMDroid map with SOS pins, "En Route" / "Resolved" status buttons |
280 | | 16–19 | Bulletin/ACK display feed, Dead Man's Switch (45-min inactivity timer in ForegroundService) |
281 | 
282 | ### Person 3 — Backend + Dashboard
283 | 
284 | | Hours | Task |
285 | |---|---|
286 | | 0–4 | Firebase project setup (Firestore collections, Hosting), dashboard scaffold (HTML + Leaflet map) |
287 | | 4–10 | Dashboard: Firestore real-time listener, color-coded SOS markers on Leaflet map, priority sidebar |
288 | | 10–14 | Bulletin creation form + Ed25519 key generation + signing logic (TweetNaCl-js for browser) |
289 | | 14–18 | ACK flow: click SOS pin → type response → sign → write to Firestore |
290 | | 18–19 | Captive Portal: NanoHTTPD server + HTML page (read bulletins + submit SOS form) |
291 | 
292 | ### Person 4 — Integration + Demo Prep
293 | 
294 | | Hours | Task |
295 | |---|---|
296 | | 0–12 | Wire networking ↔ UI: SOS created → saved to Room → sent via mesh → received → saved → displayed |
297 | | 12–16 | Wire Gateway ↔ Firebase ↔ Dashboard end-to-end |
298 | | 16–17 | Wire Captive Portal → Room → mesh |
299 | | 17–19 | **End-to-end testing on actual demo phones + demo rehearsal (minimum 2 dry runs)** |
300 | 
301 | ---
302 | 
303 | ## 10. Priority Tiers — What to Cut if Behind
304 | 
305 | | Tier | Feature | Cut Strategy |
306 | |---|---|---|
307 | | **P0 — Must Ship** | Mesh send/receive, 4-button SOS + GPS, Firebase upload, Dashboard map | Without these, no demo. |
308 | | **P1 — High Impact** | Volume SOS, Bulletin from Dashboard → phone, ACK flow | Easy to build, massive demo value. |
309 | | **P2 — Differentiator** | Captive Portal, Dead Man's Switch | Cut if behind schedule. Mention as "designed." |
310 | | **P3 — Polish** | Bloom filter sync, Power Saver mode, GPS cross-validation | Show in slides only. |
311 | 
312 | ---
313 | 
314 | ## 11. 4-Minute Demo Script
315 | 
316 | ### Setup
317 | 
318 | - **4 devices** on table: Phone 1 (Field Responder), Phone 2 (Gateway), Phone 3 (Citizen), Phone 4 (Citizen/Victim)
319 | - Phones 1, 3, 4 in **Airplane Mode** (BLE + Wi-Fi re-enabled)
320 | - Phone 2 has internet (Gateway)
321 | - Laptop showing Command Center dashboard
322 | 
323 | ### Script
324 | 
325 | | Minute | Action | What Judges See |
326 | |---|---|---|
327 | | **0:00–1:00** | Show Airplane Mode on Phones 1, 3, 4. On **Phone 4**: press Volume Down 3× — feel the haptic pulse. | 🔴 Volume SOS sent silently. "This victim is trapped in the dark." |
328 | | **1:00–2:00** | Hold Phone 4 near Phone 3 → Phone 3 near Phone 1. | SOS **hops** across the mesh. Appears on Field Responder's map as red dot with GPS. |
329 | | **2:00–3:00** | Phone 1 (Field Responder) near Phone 2 (Gateway). Point to laptop. | SOS appears on **Command Center dashboard**. Click the pin → type *"Rescue team dispatched, ETA 20 min"* → send ACK. |
330 | | **3:00–4:00** | ACK flows: Dashboard → Firebase → Gateway → Mesh → Phone 4. Show Phone 4's screen. | Victim sees: **✅ "Rescue team dispatched, ETA 20 min"**. A legacy phone connects to Phone 1's hotspot `EMERGENCY_CONNECT_HERE`, opens browser portal, sees bulletins. |
331 | 
332 | ### Closing Line
333 | 
334 | > ***"Four phones. Zero internet. A victim trapped in the dark pressed a button three times, and 60 seconds later, a rescue team was dispatched from a command center 500 kilometers away. When everything fails, Bridgefy doesn't."***
335 | 
336 | ---
337 | 
338 | ## 12. Judge Q&A — Prepared Answers
339 | 
340 | | Question | Answer |
341 | |---|---|
342 | | *"Fake SOS spam?"* | Hardware-fingerprinted rate limit (1 per 2 min). Field responders can mute devices. |
343 | | *"Battery drain?"* | BLE is ~10mW. Auto Power Saver at 30%, Emergency Beacon at 15% — survives 6–8 hrs on minimal battery. |
344 | | *"Fake government alerts?"* | Ed25519 cryptographic signatures. Private key never leaves Command Center. Even decompiling the app yields only the public key. |
345 | | *"How does data reach a remote govt facility?"* | Gateway node auto-activates on internet. Batches mesh data → Firebase. Dashboard reads in real-time. Bulletins flow back the same path. |
346 | | *"What about people without smartphones?"* | Captive Portal. Any device with Wi-Fi + browser connects to `EMERGENCY_CONNECT_HERE` hotspot. Zero download. |
347 | | *"Scale?"* | Max 10 hops + 24hr TTL + delta-sync (only missing messages). Network stays lean at hundreds of nodes. |
348 | | *"GPS indoors?"* | Falls back to last known GPS. Volume SOS + Dead Man's Switch still send location. Manual address entry available. |
349 | | *"What if no one moves?"* | Each phone is a relay. Messages propagate as people move naturally — the mesh is "carried" by human movement. In static scenarios, Wi-Fi Direct range (~200m) still covers a building. |
350 | | *"Cost?"* | Entire stack is free and open-source. ₹0 infrastructure cost. |
351 | | *"iOS support?"* | Android first — best BLE/Wi-Fi Direct support. iOS users connect via Captive Portal (no app needed). Native iOS port is future scope via MultipeerConnectivity. |
352 | 
353 | ---
354 | 
355 | ## 13. Known Risks & Mitigations
356 | 
357 | | Risk | Probability | Mitigation |
358 | |---|---|---|
359 | | BLE discovery flaky during demo | Medium | Have a **backup screen recording**. Also test in the exact demo room — BLE interference varies. |
360 | | Android OEM kills ForegroundService | Medium | Exempt app from battery optimization on demo phones. Test on actual devices early. |
361 | | Captive portal redirect doesn't auto-trigger | Medium | Fallback: tell user to open browser → `192.168.49.1`. |
362 | | Firebase quota exceeded | Low | Demo won't hit 50K reads. But have offline-only fallback ready. |
363 | | Nearby Connections API version incompatibility across phones | Low | Use same Android version on all demo phones if possible. Test cross-device early. |
364 | 
365 | ---
366 | 
367 | ## 14. File/Folder Structure (Suggested)
368 | 
369 | ```
370 | bridgefy/
371 | ├── app/
372 | │   ├── src/main/java/com/bridgefy/
373 | │   │   ├── MainActivity.kt
374 | │   │   ├── ui/
375 | │   │   │   ├── CitizenFragment.kt        # 4-button SOS
376 | │   │   │   ├── BulletinFragment.kt       # Bulletin feed
377 | │   │   │   ├── MapFragment.kt            # Community map
378 | │   │   │   └── ResponderFragment.kt      # Field Responder view
379 | │   │   ├── mesh/
380 | │   │   │   ├── MeshService.kt            # ForegroundService — BLE + WiFi Direct
381 | │   │   │   ├── NearbyManager.kt          # Nearby Connections API wrapper
382 | │   │   │   └── SyncEngine.kt             # ID exchange + delta transfer
383 | │   │   ├── gateway/
384 | │   │   │   └── GatewayManager.kt         # Firebase upload/download
385 | │   │   ├── portal/
386 | │   │   │   └── CaptivePortalServer.kt    # NanoHTTPD server
387 | │   │   ├── db/
388 | │   │   │   ├── AppDatabase.kt            # Room database
389 | │   │   │   ├── MessageDao.kt             # CRUD operations
390 | │   │   │   └── MessageEntity.kt          # Schema
391 | │   │   ├── crypto/
392 | │   │   │   └── SignatureManager.kt       # Ed25519 verify
393 | │   │   └── util/
394 | │   │       ├── DeviceFingerprint.kt      # Hardware ID
395 | │   │       ├── VolumeSosDetector.kt      # 3× Volume Down
396 | │   │       └── DeadManSwitch.kt          # 45-min inactivity
397 | │   └── res/
398 | │       └── raw/
399 | │           └── city_map.mbtiles          # Offline map tiles
400 | ├── dashboard/
401 | │   ├── index.html                         # Command Center UI
402 | │   ├── app.js                             # Leaflet map + Firestore
403 | │   └── style.css
404 | └── firebase/
405 |     └── firestore.rules
406 | ```
407 | 
408 | ---
409 | 
410 | **START TIME:** 7:49 PM  
411 | **DEADLINE:** Tomorrow 3:00 PM (19 hours)  
412 | **TEAM:** 4 people  
413 | **OUTCOME:** Working prototype + polished 4-minute demo
414 | 
415 | **Go build it. 🔥**
</content>
</file>
<file><path>Evac_Final_Project_Document.md</path>
<content lines="1-452">
  1 | # EVAC — OFFLINE DISASTER COORDINATION NETWORK
  2 | 
  3 | ## Final Project Document
  4 | 
  5 | > **When everything fails, Evac doesn't.**
  6 | 
  7 | ---
  8 | 
  9 | ## 1. Elevator Pitch
 10 | 
 11 | Evac is an Android app that turns every phone into a node in an invisible emergency network. When cell towers and internet are destroyed, victims send distress signals, rescue teams coordinate response, and officials broadcast verified alerts — **all without internet**. Messages hop silently phone-to-phone through human movement. A Gateway at the disaster's edge bridges the mesh to a cloud dashboard accessible worldwide. People without the app connect through a Wi-Fi portal — **no download needed**.
 12 | 
 13 | ---
 14 | 
 15 | ## 2. Architecture — Three Zones
 16 | 
 17 | ```
 18 | ┌──────────────────────────────────────────────────────────────────┐
 19 | │  ZONE A — DISASTER ZONE  (No Internet)                           │
 20 | │                                                                  │
 21 | │  📱 Citizen ◄──BLE/WiFi──► 📱 Citizen ◄──BLE/WiFi──► 📱 Field  │
 22 | │       │                         │                   Responder    │
 23 | │       │                         │                       │        │
 24 | │       └─────── BLE/WiFi ────────┘                  BLE/WiFi      │
 25 | │                                                         │        │
 26 | │                  📱 Legacy Phone ──WiFi──► 📶 Captive Portal     │
 27 | └──────────────────────────────────────────────────────────────────┘
 28 |                                                          │
 29 |                                               Satellite / LoRa /
 30 |                                               4G / SMS
 31 |                                                          │
 32 | ┌──────────────────────────────────────────────────────────────────┐
 33 | │  ZONE C — THE BRIDGE  (Edge of Disaster)                         │
 34 | │  📡 Gateway Node (phone with internet connection)                │
 35 | │  Uploads mesh data → Cloud  |  Downloads bulletins → Mesh        │
 36 | └──────────────────────────────────────────────────────────────────┘
 37 |                                                          │
 38 |                                                      Internet
 39 |                                                          │
 40 | ┌──────────────────────────────────────────────────────────────────┐
 41 | │  ZONE B — COMMAND CENTER  (Remote, Has Internet)                 │
 42 | │  🖥️ Web Dashboard: Live SOS map, verified bulletins, ACKs       │
 43 | │  🗄️ Firebase Firestore: Persistent data + real-time sync        │
 44 | └──────────────────────────────────────────────────────────────────┘
 45 | ```
 46 | 
 47 | **Key Principle:** The mesh is **fully autonomous**. The Gateway is an *enhancement*, not a dependency. If it goes down, citizens and field responders keep communicating.
 48 | 
 49 | ---
 50 | 
 51 | ## 3. Five Node Types
 52 | 
 53 | | Node | Activation | Capabilities |
 54 | |---|---|---|
 55 | | **Citizen** | Default on install | 4-button SOS, Volume SOS, receive bulletins, receive ACKs |
 56 | | **Field Responder** | PIN-gated (production: Ed25519 keypair) | All Citizen abilities **+** offline SOS map, "En Route"/"Resolved" status, activate Captive Portal |
 57 | | **Gateway** | Auto-activates when internet detected | Mesh participant **+** batches data → Firebase, injects bulletins back into mesh |
 58 | | **Legacy Portal User** | No app needed | Connects to `EVAC_EMERGENCY` Wi-Fi hotspot, uses browser portal to read bulletins + submit SOS |
 59 | | **Command Center** | Web dashboard (separate) | Live SOS map, issue signed bulletins, send signed ACKs to victims |
 60 | 
 61 | ---
 62 | 
 63 | ## 4. Core Features
 64 | 
 65 | ### 🔴 Feature 1: Four-Button SOS Interface
 66 | 
 67 | | Button | Code | Color | Use Case |
 68 | |---|---|---|---|
 69 | | MEDICAL | `MED` | Red | Injuries, medical emergencies |
 70 | | TRAPPED | `TRP` | Orange | Stuck under debris, can't move |
 71 | | HAZARD | `HAZ` | Yellow | Downed powerline, gas leak, flood |
 72 | | SAFE | `SAF` | Green | "I'm okay" — clears prior SOS |
 73 | 
 74 | - **One tap** sends SOS with automatic GPS — zero typing under stress
 75 | - Optional short text note (100 chars) for details
 76 | - **People count selector** (1–10+) — critical for rescue triage: *"5 people trapped"*
 77 | - **Battery level auto-included** — responders see if victim's phone is dying and prioritize
 78 | - Rate-limited: **1 SOS per 2 minutes** per device (hardware fingerprinted)
 79 | 
 80 | ---
 81 | 
 82 | ### 📳 Feature 2: Volume SOS
 83 | 
 84 | - Press **Volume Down 3× fast** = instant distress signal
 85 | - Works with **screen off**, in the dark, in your pocket
 86 | - **Haptic pulse** confirmation only (silent — critical if trapped near danger)
 87 | - Sends with last known GPS + `TRAPPED` status + battery level
 88 | - Detected via Android `MediaSession` callback — works even when screen is locked
 89 | 
 90 | ---
 91 | 
 92 | ### 📡 Feature 3: Offline Mesh Network
 93 | 
 94 | ```
 95 | Phone A                              Phone B
 96 |    │                                    │
 97 |    ├── BLE Advertise (custom UUID) ────►│
 98 |    │◄── BLE Discover ──────────────────┤
 99 |    │                                    │
100 |    ├── Upgrade to Wi-Fi Direct ────────►│
101 |    │                                    │
102 |    ├── Exchange message ID lists ──────►│
103 |    │◄── "I need: [a,c]. Here's [d]" ───┤
104 |    │                                    │
105 |    │   Transfer only MISSING messages   │
106 |    │   Priority order: CRITICAL first   │
107 |    │                                    │
108 |    ├── Verify SHA-256 hash ────────────►│
109 |    │◄── Verify SHA-256 hash ───────────┤
110 |    │                                    │
111 |    └── Disconnect. Target: <3 sec ─────►│
112 | ```
113 | 
114 | - **BLE** for discovery (ultra-low power, ~10mW)
115 | - **Wi-Fi Direct** for high-speed data transfer
116 | - Messages hop automatically — no user action
117 | - **Max 10 hops** per message (prevents flooding)
118 | - **TTL: 24 hours** default (stale messages auto-purged)
119 | - **Auto-rebroadcast:** Active SOS signals are re-broadcast every 10 minutes so rescuers approaching the area pick them up even if the original sender has moved or lost power
120 | 
121 | ---
122 | 
123 | ### 🌉 Feature 4: Gateway Bridge
124 | 
125 | - Any phone with internet **auto-activates** as a Gateway
126 | - **Mesh → Cloud:** Batches all new data every 5 min → uploads to Firebase Firestore
127 | - **Cloud → Mesh:** Pulls new bulletins/ACKs from Firebase → injects into mesh
128 | - Multiple gateways = redundancy; Firebase deduplicates via unique message IDs
129 | - If gateway goes down, mesh continues; syncs backlog on recovery
130 | 
131 | ---
132 | 
133 | ### 📶 Feature 5: Captive Portal (Legacy Device Support)
134 | 
135 | - Field Responder activates Wi-Fi hotspot: **`EVAC_EMERGENCY`**
136 | - **NanoHTTPD** (embedded HTTP server) serves a clean HTML page
137 | - ₹500 button phones, iPhones, laptops — anything with Wi-Fi + browser works
138 | - Portal: read bulletins + submit SOS (name, location description, status)
139 | - **Zero download, zero sign-up**
140 | 
141 | > [!NOTE]
142 | > Captive portal auto-redirect varies by device. Fallback: user opens browser → `192.168.49.1`
143 | 
144 | ---
145 | 
146 | ### 🖥️ Feature 6: Command Center Dashboard
147 | 
148 | - **Web app** (HTML/JS + Leaflet.js) hosted on Firebase Hosting (free)
149 | - **Live map** with color-coded SOS pins:
150 | 
151 | | Color | Meaning |
152 | |---|---|
153 | | 🔴 Red | Medical emergency |
154 | | 🟠 Orange | Trapped |
155 | | 🟡 Yellow | Hazard report |
156 | | 🟢 Green | Safe / Resolved |
157 | 
158 | - **Issue bulletins** — typed, signed with Ed25519, pushed to Firebase → Gateway → Mesh
159 | - **Send ACKs** — click SOS pin → type *"Help dispatched, ETA 30 min"* → signed → sent back to victim
160 | - **Priority sidebar** — ranks zones by threat density (count of active MEDICAL + TRAPPED SOSes per area)
161 | - **Pin details** show: status, people count, battery level, time since last update
162 | 
163 | ---
164 | 
165 | ### 🌐 Feature 7: Multi-Language Emergency Phrases
166 | 
167 | - Pre-loaded quick phrases in **5 languages** (Hindi, English, Telugu, Tamil, Bengali)
168 | - Victim taps a phrase instead of typing: *"I need water"*, *"Child injured"*, *"Building collapsed"*
169 | - Overcomes language barriers between rescue teams from other states and local victims
170 | - Takes 30 minutes to implement (just a string array + UI list)
171 | 
172 | ---
173 | 
174 | ## 5. ~~Removed~~ Features (Not Practical for 19hrs)
175 | 
176 | | Feature | Why Removed |
177 | |---|---|
178 | | **Dead Man's Switch** (45-min auto-broadcast) | Android OEMs (Xiaomi, Samsung, Huawei) aggressively kill `ForegroundService`. False positive rate is high — phone in pocket for 45 min is normal. Would flood the network with welfare-check beacons. **Mention as future scope instead.** |
179 | | **Bloom Filter sync** | Over-engineered for 3-phone demo. Simple ID-list exchange achieves the same result. Mention Bloom filters as "production optimization" to judges. |
180 | | **Lamport Clocks** | Phones have local clocks even offline. Simple `System.currentTimeMillis()` timestamps work. Clock drift across phones is negligible for a 24-hour disaster window. |
181 | | **Binary protocol (26 bytes)** | Custom binary serialization is bug-prone and hard to debug at 3 AM. JSON is readable, debuggable, and Nearby Connections handles the bandwidth fine for a demo. |
182 | | **GPS cross-validation** | Requires knowing relay chain geography — complex and unreliable. Not worth the implementation time. |
183 | 
184 | ---
185 | 
186 | ## 6. Message Schema (JSON)
187 | 
188 | ### SOS Message
189 | 
190 | ```json
191 | {
192 |   "id": "uuid-v4",
193 |   "type": "SOS",
194 |   "status": "MEDICAL | TRAPPED | HAZARD | SAFE",
195 |   "device_id": "sha256(android_id + ble_mac)",
196 |   "timestamp": "2026-03-13T20:00:00Z",
197 |   "ttl_hours": 24,
198 |   "hop_count": 0,
199 |   "max_hops": 10,
200 |   "lat": 17.385,
201 |   "lng": 78.4867,
202 |   "accuracy_m": 10,
203 |   "people_count": 3,
204 |   "battery_pct": 42,
205 |   "note": "3rd floor, near stairwell. 2 adults, 1 child.",
206 |   "phrase_key": "CHILD_INJURED",
207 |   "is_volume_sos": false,
208 |   "hash": "sha256-of-all-fields-except-hash"
209 | }
210 | ```
211 | 
212 | ### Bulletin Message
213 | 
214 | ```json
215 | {
216 |   "id": "uuid-v4",
217 |   "type": "BULLETIN",
218 |   "alert_type": "FLOOD | EARTHQUAKE | CYCLONE | GENERAL",
219 |   "affected_zone": { "lat": 17.4, "lng": 78.5, "radius_km": 5 },
220 |   "body": "Flash flood warning. Move to higher ground immediately.",
221 |   "timestamp": "2026-03-13T20:00:00Z",
222 |   "ttl_hours": 12,
223 |   "hop_count": 0,
224 |   "max_hops": 10,
225 |   "ed25519_signature": "base64-encoded-64-bytes",
226 |   "hash": "sha256-of-all-fields-except-hash-and-sig"
227 | }
228 | ```
229 | 
230 | ### ACK Message
231 | 
232 | ```json
233 | {
234 |   "id": "uuid-v4",
235 |   "type": "ACK",
236 |   "target_device_id": "sha256-of-victim-device",
237 |   "body": "Rescue team dispatched. ETA 30 minutes. Stay where you are.",
238 |   "timestamp": "2026-03-13T20:05:00Z",
239 |   "ttl_hours": 6,
240 |   "hop_count": 0,
241 |   "max_hops": 10,
242 |   "ed25519_signature": "base64-encoded-64-bytes",
243 |   "hash": "sha256-of-all-fields-except-hash-and-sig"
244 | }
245 | ```
246 | 
247 | ---
248 | 
249 | ## 7. Security Model
250 | 
251 | | Threat | Mitigation |
252 | |---|---|
253 | | Fake SOS spam | Hardware fingerprint rate limit: **1 SOS per 2 min**. Field Responders can **mute** a device. |
254 | | Fake bulletins / ACKs | **Ed25519 signature**. Public key in app. Private key only on Command Center. |
255 | | Message tampering | **SHA-256 hash** per message. Tampered = dropped. |
256 | | Stale information | **TTL** field — expired messages purged every sync. |
257 | | Network flooding | **Max 10 hops**. Messages beyond limit dropped. |
258 | | Replay attacks | Reject messages with same `id` (UUID deduplication). |
259 | | Device ID spoofing | `sha256(android_id + BLE_MAC)` — survives app reinstall. |
260 | 
261 | ---
262 | 
263 | ## 8. Power Management
264 | 
265 | | Mode | Trigger | BLE Scan | GPS | Est. Battery |
266 | |---|---|---|---|---|
267 | | **Normal** | Default | Every 30s | Every 60s | ~8 hrs |
268 | | **Power Saver** | Battery ≤ 30% | Every 5 min | Every 5 min | ~18 hrs |
269 | | **Emergency Beacon** | Battery ≤ 15% | Minimal broadcast | Off (last known) | ~6–8 hrs |
270 | 
271 | Auto-switch is handled in the `ForegroundService`. No user action needed.
272 | 
273 | ---
274 | 
275 | ## 9. Tech Stack (₹0 Total)
276 | 
277 | | Component | Technology |
278 | |---|---|
279 | | Mobile App | Android Native (Kotlin) |
280 | | Mesh Discovery | BLE (Android SDK) |
281 | | Mesh Transfer | Nearby Connections API |
282 | | Local Database | Room (SQLite) |
283 | | Captive Portal | NanoHTTPD |
284 | | Offline Maps | OSMDroid |
285 | | Crypto | TweetNaCl-java (Ed25519) |
286 | | Cloud Backend | Firebase Firestore (free tier) |
287 | | Dashboard | HTML/JS + Leaflet.js |
288 | | Hosting | Firebase Hosting (free tier) |
289 | 
290 | ---
291 | 
292 | ## 10. 19-Hour Build Plan (4 People)
293 | 
294 | **Start:** 7:49 PM  |  **Deadline:** Tomorrow 3:00 PM
295 | 
296 | ### Person 1 — Mesh Networking 🔴 Critical Path
297 | 
298 | | Hours | Task |
299 | |---|---|
300 | | 0–3 | Nearby Connections API "hello world" — send a string between 2 phones |
301 | | 3–8 | Store-and-forward relay: Phone A → Phone B → Phone C |
302 | | 8–12 | BLE discovery + continuous background scanning via ForegroundService |
303 | | 12–16 | Sync protocol: exchange ID lists → transfer missing messages, CRITICAL first |
304 | | 16–19 | Gateway: batch upload to Firebase + pull bulletins into mesh |
305 | 
306 | > [!CAUTION]
307 | > **If mesh isn't working by Hour 5**, pivot to phones on same local Wi-Fi exchanging messages. Show BLE architecture in slides. A working demo on Wi-Fi beats a broken demo on BLE.
308 | 
309 | ### Person 2 — Mobile App UI
310 | 
311 | | Hours | Task |
312 | |---|---|
313 | | 0–4 | App scaffold: ForegroundService, Room DB, device fingerprint, bottom navigation |
314 | | 4–8 | 4-button SOS UI, people count selector, GPS grab, battery level auto-capture |
315 | | 8–12 | Volume SOS: 3× Volume Down detection via MediaSession, haptic confirm |
316 | | 12–16 | Field Responder mode: PIN gate, OSMDroid map with color-coded SOS pins, status buttons |
317 | | 16–19 | Bulletin/ACK display feed, multi-language phrase selector, auto-rebroadcast toggle |
318 | 
319 | ### Person 3 — Backend + Dashboard
320 | 
321 | | Hours | Task |
322 | |---|---|
323 | | 0–4 | Firebase project (Firestore + Hosting), dashboard scaffold (HTML + Leaflet) |
324 | | 4–10 | Dashboard: Firestore listener, color-coded SOS markers, pin details (people, battery, time) |
325 | | 10–14 | Bulletin form + Ed25519 signing (TweetNaCl-js in browser) |
326 | | 14–18 | ACK flow: click pin → type response → sign → Firestore. Priority sidebar. |
327 | | 18–19 | Captive Portal: NanoHTTPD + HTML page (bulletins + SOS form) |
328 | 
329 | ### Person 4 — Integration + Demo
330 | 
331 | | Hours | Task |
332 | |---|---|
333 | | 0–12 | Wire networking ↔ UI: SOS → Room → mesh → received → saved → displayed |
334 | | 12–16 | Wire Gateway ↔ Firebase ↔ Dashboard (both directions) |
335 | | 16–17 | Wire Captive Portal → Room → mesh |
336 | | 17–19 | **End-to-end testing + demo rehearsal (minimum 2 full dry runs)** |
337 | 
338 | ---
339 | 
340 | ## 11. Priority Tiers — What to Cut
341 | 
342 | | Tier | Features | Rule |
343 | |---|---|---|
344 | | **P0 — Must Ship** | Mesh send/receive, 4-button SOS + GPS, Firebase upload, Dashboard map | No demo without these |
345 | | **P1 — High Impact** | Volume SOS, Bulletin → phone, ACK → victim, people count + battery in SOS | Easy wins, big demo value |
346 | | **P2 — Differentiator** | Captive Portal, multi-language phrases, auto-rebroadcast | Cut if behind. Show in slides. |
347 | | **P3 — Polish** | Power Saver mode, priority sidebar, offline map tiles | Mention only |
348 | 
349 | ---
350 | 
351 | ## 12. 4-Minute Demo Script
352 | 
353 | ### Setup
354 | - **4 devices:** Phone 1 (Field Responder), Phone 2 (Gateway), Phone 3 (Citizen), Phone 4 (Victim)
355 | - Phones 1, 3, 4 → **Airplane Mode** (BLE + Wi-Fi re-enabled)
356 | - Phone 2 has internet (Gateway)
357 | - Laptop showing Command Center dashboard
358 | 
359 | ### Script
360 | 
361 | | Min | Action | Judges See |
362 | |---|---|---|
363 | | 0:00 | Show Airplane Mode on 3 phones. "No internet. No cell towers." | Credibility. |
364 | | 0:30 | **Phone 4:** Press Volume Down 3× in pocket. Feel haptic. | *"Victim is trapped in the dark. One hand free."* |
365 | | 1:00 | Hold Phone 4 near Phone 3, then Phone 3 near Phone 1. | SOS **hops** across mesh. Red dot appears on Responder's map: "TRAPPED — 3 people — Battery 34%". |
366 | | 1:30 | Phone 1 taps "En Route" on the SOS pin. | Status changes to "Responder dispatched." |
367 | | 2:00 | Phone 1 near Phone 2 (Gateway). Point to laptop. | SOS appears on **Command Center dashboard** with all details. |
368 | | 2:30 | On dashboard: click pin → type *"Helicopter ETA 20 min"* → send ACK. | ACK flows: Dashboard → Firebase → Gateway → Mesh → Phone 4. |
369 | | 3:00 | Show Phone 4: ACK received — **"✅ Helicopter ETA 20 min"** | *"The victim knows help is coming."* |
370 | | 3:30 | Legacy phone connects to `EVAC_EMERGENCY` hotspot. Browser opens. Submits SOS. | Appears on dashboard. *"No app needed."* |
371 | | 4:00 | Closing. | |
372 | 
373 | ### Closing Line
374 | 
375 | > ***"Four phones. Zero internet. A victim trapped in the dark pressed a button three times. Sixty seconds later, a command center 500 km away dispatched a helicopter. When everything fails, Evac doesn't."***
376 | 
377 | ---
378 | 
379 | ## 13. Judge Q&A
380 | 
381 | | Question | Answer |
382 | |---|---|
383 | | *"Fake SOS?"* | Hardware fingerprint rate limit (1 per 2 min) + responder mute. |
384 | | *"Battery drain?"* | BLE ~10mW. Auto-saver at 30%. Emergency beacon at 15% lasts 6–8 hrs. |
385 | | *"Fake alerts?"* | Ed25519 signatures. Private key only on Command Center. |
386 | | *"Remote govt facility?"* | Gateway auto-bridges mesh → Firebase → Dashboard. Works globally. |
387 | | *"No smartphone?"* | Captive Portal: any Wi-Fi device + browser. Zero download. |
388 | | *"Scale?"* | 10-hop max + 24hr TTL + delta-sync. Network stays lean. |
389 | | *"GPS indoors?"* | Last known GPS + manual text description. |
390 | | *"Nobody moves?"* | Wi-Fi Direct ~200m covers a building. Auto-rebroadcast every 10 min. |
391 | | *"Cost?"* | ₹0. 100% free/open-source. |
392 | | *"iOS?"* | Captive Portal works for iOS. Native port is future scope. |
393 | 
394 | ---
395 | 
396 | ## 14. Suggested Project Structure
397 | 
398 | ```
399 | evac/
400 | ├── app/src/main/java/com/evac/
401 | │   ├── MainActivity.kt
402 | │   ├── ui/
403 | │   │   ├── CitizenFragment.kt         # 4-button SOS + phrase selector
404 | │   │   ├── BulletinFragment.kt        # Bulletin + ACK feed
405 | │   │   ├── MapFragment.kt             # OSMDroid map (Responder)
406 | │   │   └── ResponderFragment.kt       # Status controls
407 | │   ├── mesh/
408 | │   │   ├── MeshService.kt             # ForegroundService (BLE + WiFi Direct)
409 | │   │   ├── NearbyManager.kt           # Nearby Connections wrapper
410 | │   │   └── SyncEngine.kt              # ID exchange + delta transfer
411 | │   ├── gateway/
412 | │   │   └── GatewayManager.kt          # Firebase upload/download
413 | │   ├── portal/
414 | │   │   └── CaptivePortalServer.kt     # NanoHTTPD
415 | │   ├── db/
416 | │   │   ├── AppDatabase.kt             # Room
417 | │   │   ├── MessageDao.kt
418 | │   │   └── MessageEntity.kt
419 | │   ├── crypto/
420 | │   │   └── SignatureManager.kt        # Ed25519 verify
421 | │   └── util/
422 | │       ├── DeviceFingerprint.kt
423 | │       ├── VolumeSosDetector.kt        # 3× Volume Down
424 | │       └── Phrases.kt                 # Multi-language strings
425 | ├── dashboard/
426 | │   ├── index.html
427 | │   ├── app.js                          # Leaflet + Firestore
428 | │   └── style.css
429 | └── firebase/
430 |     └── firestore.rules
431 | ```
432 | 
433 | ---
434 | 
435 | ## 15. Future Scope (Mention if Judges Ask)
436 | 
437 | - **Dead Man's Switch** — auto-broadcast if no user interaction for 45 min (needs OEM-specific tuning)
438 | - **AI triage** — on-device ML to prioritize SOS signals
439 | - **Bloom filter sync** — reduce bandwidth at scale
440 | - **Binary protocol** — 26-byte compact format for BLE efficiency
441 | - **Drone relay nodes** — extend mesh coverage
442 | - **NDRF/SDRF integration** — CAP (Common Alerting Protocol) format
443 | - **iOS native app** — via MultipeerConnectivity framework
444 | 
445 | ---
446 | 
447 | **START TIME:** 7:49 PM  
448 | **DEADLINE:** Tomorrow 3:00 PM (19 hours)  
449 | **TEAM:** 4 people  
450 | **OUTCOME:** Working prototype + polished 4-minute demo
451 | 
452 | **Go build it. 🔥**
</content>
</file>
</files>
<environment_details>
# VSCode Visible Files
../Downloads/bob_task_may-16-2026_8-08-48-pm.md

# VSCode Open Tabs
scripts/validate_compliance_report.py,reports/sample_report.json,../Downloads/bob_task_may-16-2026_8-08-48-pm.md,.github/workflows/vsae-gate.yml

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T14:47:55.568Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.03

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

I can see the two files that need to be removed. Let me delete them and push the changes to git.

<execute_command>
<command>git rm Bridgefy_Final_Project_Document.md.resolved Evac_Final_Project_Document.md</command>
</execute_command>

---

**User:**

[execute_command for 'git rm Bridgefy_Final_Project_Document.md.resolved Evac_Final_Project_Document.md'] Result:
Command executed in terminal  within working directory '/Users/jason/vsae'. Exit code: 0
Output:
rm 'Bridgefy_Final_Project_Document.md.resolved'
rm 'Evac_Final_Project_Document.md'

<environment_details>
# VSCode Visible Files
Bridgefy_Final_Project_Document.md.resolved

# VSCode Open Tabs
scripts/validate_compliance_report.py,reports/sample_report.json,Bridgefy_Final_Project_Document.md.resolved,.github/workflows/vsae-gate.yml

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T14:48:02.928Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.11

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Good! The files have been removed from git. Now let me commit this change and push it to the remote repository.

<execute_command>
<command>git commit -m "Remove Bridgefy and Evac project documents"</command>
</execute_command>

---

**User:**

[execute_command for 'git commit -m "Remove Bridgefy and Evac project documents"'] Result:
Command executed in terminal  within working directory '/Users/jason/vsae'. Exit code: 0
Output:
[main 61b2991] Remove Bridgefy and Evac project documents
 2 files changed, 867 deletions(-)
 delete mode 100644 Bridgefy_Final_Project_Document.md.resolved
 delete mode 100644 Evac_Final_Project_Document.md

<environment_details>
# VSCode Visible Files
Bridgefy_Final_Project_Document.md.resolved

# VSCode Open Tabs
scripts/validate_compliance_report.py,reports/sample_report.json,Bridgefy_Final_Project_Document.md.resolved,.github/workflows/vsae-gate.yml

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T14:48:10.112Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.18

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

Perfect! The commit was successful. Now let me push the changes to the remote repository.

<execute_command>
<command>git push</command>
</execute_command>

---

**User:**

[execute_command for 'git push'] Result:
Command executed in terminal  within working directory '/Users/jason/vsae'. Exit code: 0
Output:
To https://github.com/irudayajason/VSAE.git
   7f7a6f7..61b2991  main -> main

<environment_details>
# VSCode Visible Files
Bridgefy_Final_Project_Document.md.resolved

# VSCode Open Tabs
scripts/validate_compliance_report.py,reports/sample_report.json,Bridgefy_Final_Project_Document.md.resolved,.github/workflows/vsae-gate.yml

# Current Time
Current time in ISO 8601 UTC format: 2026-05-16T14:48:18.122Z
User time zone: Asia/Calcutta, UTC+5:30

# Current Cost
$0.26

# Review Exclusions
The following file patterns are excluded from code reviews:
- .vscode/**

# Current Mode
<slug>advanced</slug>
<name>🛠️ Advanced</name>
You have not created a todo list yet. Create one with `update_todo_list` if your task is complicated or involves multiple steps.
</environment_details>

---

**Assistant:**

<attempt_completion>
<result>
Successfully removed both files from the repository and pushed to git:
- [`Bridgefy_Final_Project_Document.md.resolved`](Bridgefy_Final_Project_Document.md.resolved)
- [`Evac_Final_Project_Document.md`](Evac_Final_Project_Document.md)

Changes pushed to remote repository (commit 61b2991).
</result>
</attempt_completion>

