const MUTE_KEY = 'mood-tracker.recap-muted'

/** Soft mid notes — high enough to avoid ear rumble, low enough to stay quiet. */
const SCALE = [329.63, 349.23, 392.0, 415.3, 440.0, 493.88]

type RecapPhase = 'form' | 'orbit' | 'reveal'

export type RecapHoverKind = 'mood' | 'tag' | 'goal'

export type RecapSoundHandle = {
  setPhase: (phase: RecapPhase) => void
  setMuted: (muted: boolean) => void
  playHover: (kind: RecapHoverKind, id: string) => void
  stop: (quick?: boolean) => void
}

type RecapSoundOptions = {
  seed: number
  mood: number
  muted: boolean
  orbitMs: number
}

function AudioContextCtor(): typeof AudioContext | null {
  if (typeof window === 'undefined') {
    return null
  }
  const fromWindow = window as Window & { webkitAudioContext?: typeof AudioContext }
  return window.AudioContext ?? fromWindow.webkitAudioContext ?? null
}

let sharedContext: AudioContext | null = null

export function isRecapSoundMuted(): boolean {
  try {
    return window.localStorage.getItem(MUTE_KEY) === '1'
  } catch {
    return false
  }
}

export function persistRecapSoundMuted(muted: boolean): void {
  try {
    window.localStorage.setItem(MUTE_KEY, muted ? '1' : '0')
  } catch {
    /* ignore quota / private mode */
  }
}

/** Call from a click handler so the browser allows playback. */
export function primeRecapAudio(): AudioContext | null {
  const Ctor = AudioContextCtor()
  if (!Ctor) {
    return null
  }
  if (!sharedContext || sharedContext.state === 'closed') {
    sharedContext = new Ctor()
  }
  void sharedContext.resume()
  return sharedContext
}

function hashTone(id: string): number {
  let hash = 2166136261
  for (let i = 0; i < id.length; i += 1) {
    hash ^= id.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

function hoverFreq(kind: RecapHoverKind, id: string): number {
  const degree = hashTone(`${kind}:${id}`) % SCALE.length
  return SCALE[degree] ?? SCALE[0]
}

export function startRecapSound(options: RecapSoundOptions): RecapSoundHandle | null {
  const ctx = primeRecapAudio()
  if (!ctx) {
    return null
  }

  let stopped = false
  let muted = options.muted
  let lastHoverId = ''
  let lastHoverAt = 0

  const master = ctx.createGain()
  master.gain.value = muted ? 0 : 1
  master.connect(ctx.destination)

  const filter = ctx.createBiquadFilter()
  filter.type = 'lowpass'
  filter.frequency.value = 1600
  filter.Q.value = 0.3
  filter.connect(master)

  return {
    setPhase: () => {
      /* Background stays silent — no drone. */
    },
    setMuted: (next) => {
      muted = next
      persistRecapSoundMuted(next)
      if (stopped) {
        return
      }
      const time = ctx.currentTime
      master.gain.cancelScheduledValues(time)
      master.gain.setValueAtTime(master.gain.value, time)
      master.gain.linearRampToValueAtTime(next ? 0 : 1, time + 0.08)
    },
    playHover: (kind, id) => {
      if (stopped || muted || !id) {
        return
      }
      const nowMs = performance.now()
      if (id === lastHoverId && nowMs - lastHoverAt < 520) {
        return
      }
      if (nowMs - lastHoverAt < 140) {
        return
      }
      lastHoverId = id
      lastHoverAt = nowMs

      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = hoverFreq(kind, id)
      gain.gain.value = 0
      osc.connect(gain).connect(filter)
      const t = ctx.currentTime
      gain.gain.setValueAtTime(0, t)
      gain.gain.linearRampToValueAtTime(0.035, t + 0.08)
      gain.gain.linearRampToValueAtTime(0, t + 0.38)
      osc.start(t)
      osc.stop(t + 0.42)
    },
    stop: () => {
      if (stopped) {
        return
      }
      stopped = true
      const time = ctx.currentTime
      master.gain.cancelScheduledValues(time)
      master.gain.setValueAtTime(master.gain.value, time)
      master.gain.linearRampToValueAtTime(0, time + 0.08)
    },
  }
}
