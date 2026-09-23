/** Matches backend `MAX_AUDIO_BYTES` in mood_entry_service. */
export const MAX_AUDIO_BYTES = 10 * 1024 * 1024

/** Safety cap so a recording cannot run indefinitely. */
export const MAX_AUDIO_RECORDING_MS = 10 * 60 * 1000

const RECORDER_MIME_CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
]

export function isAudioRecordingSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.isSecureContext &&
    typeof MediaRecorder !== 'undefined' &&
    typeof navigator.mediaDevices?.getUserMedia === 'function'
  )
}

export function pickAudioRecorderMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') {
    return undefined
  }
  return RECORDER_MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type))
}

export function formatAudioClock(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) {
    return '0:00'
  }
  const total = Math.floor(totalSeconds)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function extensionForAudioMime(mime: string): string {
  const base = mime.split(';')[0]?.trim().toLowerCase() ?? ''
  if (base === 'audio/ogg') {
    return 'ogg'
  }
  if (base === 'audio/mp4' || base === 'audio/aac') {
    return 'm4a'
  }
  if (base === 'audio/mpeg') {
    return 'mp3'
  }
  if (base === 'audio/wav' || base === 'audio/x-wav') {
    return 'wav'
  }
  return 'webm'
}

export function recordingBlobToFile(blob: Blob, recorderMimeType?: string): File {
  const rawType = blob.type || recorderMimeType || 'audio/webm'
  const type = rawType.split(';')[0]?.trim() || 'audio/webm'
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  return new File([blob], `recording-${stamp}.${extensionForAudioMime(type)}`, { type })
}

export function stopMediaStream(stream: MediaStream | null): void {
  if (!stream) {
    return
  }
  for (const track of stream.getTracks()) {
    track.stop()
  }
}
