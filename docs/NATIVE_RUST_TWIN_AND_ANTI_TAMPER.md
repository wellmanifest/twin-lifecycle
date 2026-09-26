# Native Rust Twin Runtime and Anti-Tamper Standard

## 1. Overview and Invariants

This standard specifies the runtime requirements for high-performance Digital Twin virtualization engines within the Wellmanifest ecosystem.

To guarantee deterministic isolation, sub-second startup latency, and defense against intellectual property theft or runtime tampering, conforming twin implementations MUST fulfill the following core invariants:

### Core Invariants:

1. `twin-native-rust-engine`
   - The virtualization core MUST be compiled as native stripped ELF binaries (`twinerd`, `clonerd-twin`) without interpreter overhead.
   - Startup latency for ephemeral sandboxes and workstation instances MUST be under 1.0 second.

2. `twin-overlayfs-cow-isolation`
   - Runtime filesystem virtualization MUST leverage Linux OverlayFS Copy-on-Write (CoW).
   - Base templates MUST remain strictly read-only (`ro`); all mutations occur within ephemeral upper directories.
   - Discarding a corrupted or compromised twin MUST be an atomic metadata directory removal (`rm -rf upper/ work/`), leaving base snapshots untouched.

3. `twin-anti-debug-runtime-tripwire`
   - Binaries MUST actively inspect runtime debug states (`/proc/self/status` `TracerPid != 0` or `ptrace(PTRACE_TRACEME)`).
   - If an unauthorized debugger, tracer, or dynamic instrumentation framework is detected, the engine MUST terminate immediately (`abort()`) without revealing memory layouts or symbol tables.

4. `twin-cabi-guard-interface`
   - Shared libraries (`libtwinerd_guard.so`) MUST expose an extern "C" ABI compatible with Python `ctypes`, Go `cgo`, and C/C++ runtimes.
   - The guard library validates license tokens, hardware node fingerprints (CPU model, machine-id, MAC digest), and cryptographic Ed25519 signatures.

5. `twin-hardware-drm-licensing`
   - Enterprise and on-premise twin runtimes MUST be cryptographically bound to hardware fingerprints.
   - All intellectual property, copyright, and patent claims remain under exclusive ownership:
     `Tomasz Sapletta Prototypowanie.pl NIP: 5881918662, REGON: 220665410`.

6. `twin-rfb-websocket-bridge`
   - Remote framebuffer streaming MUST implement native Tokio asynchronous RFB/VNC-to-WebSocket bridging.
   - Web clients connect directly via HTML5 canvas/WebSocket without requiring external VNC proxy daemons (e.g. websockify).

---

## 2. Architecture Diagram

```
+--------------------------------------------------------------------------+
|                     TWINERD NATIVE VIRTUALIZATION CORE                   |
|                                                                          |
|  - Compiled Binary: /usr/local/bin/twinerd (0.2.0, stripped ELF)        |
|  - C-ABI Guard: /usr/local/lib/libtwinerd_guard.so                      |
|  - Async Runtime: Tokio Event Loop + RFB/VNC-to-WebSocket Bridge         |
+------------------------------------+-------------------------------------+
                                     |
                Linux Kernel Primitives & Sandboxing
                                     |
        +----------------------------+----------------------------+
        |                                                         |
        v                                                         v
+-------------------------------+         +-------------------------------+
|  OverlayFS CoW Storage        |         |  Anti-Tamper & Security Guard |
|                               |         |                               |
|  - LowerDir: base snapshot ro |         |  - TracerPid == 0 Tripwire    |
|  - UpperDir: ephemeral delta  |         |  - Obfuscated string tables   |
|  - WorkDir: atomic commit     |         |  - Ed25519 Signature Verifier |
|  - Instant reset (< 50ms)     |         |  - Node Hardware DRM Binding  |
+-------------------------------+         +-------------------------------+
```

---

## 3. Conformance Verification

A conforming engine MUST pass:
```bash
# 1. Verification of binary stripping and anti-debug
twinerd inspect

# 2. C-ABI ctypes verification
python3 -c "import ctypes; guard = ctypes.CDLL('/usr/local/lib/libtwinerd_guard.so'); assert guard.twinerd_guard_init() == 0"
```
