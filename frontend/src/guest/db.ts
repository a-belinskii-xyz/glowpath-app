const DB_NAME = 'mood_tracker_guest'
const STORE_NAME = 'kv'
const DB_VERSION = 1

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onerror = () => reject(request.error ?? new Error('IndexedDB open failed'))
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME)
      }
    }
    request.onsuccess = () => resolve(request.result)
  })
}

export async function guestDbGet<T>(key: string): Promise<T | null> {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const request = store.get(key)
    request.onerror = () => reject(request.error ?? new Error('IndexedDB get failed'))
    request.onsuccess = () => resolve((request.result as T | undefined) ?? null)
    tx.oncomplete = () => db.close()
  })
}

export async function guestDbSet<T>(key: string, value: T): Promise<void> {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const request = store.put(value, key)
    request.onerror = () => reject(request.error ?? new Error('IndexedDB put failed'))
    request.onsuccess = () => resolve()
    tx.oncomplete = () => db.close()
  })
}

export async function guestDbClear(): Promise<void> {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const request = store.clear()
    request.onerror = () => reject(request.error ?? new Error('IndexedDB clear failed'))
    request.onsuccess = () => resolve()
    tx.oncomplete = () => db.close()
  })
}

export async function guestDbDeleteDatabase(): Promise<void> {
  await guestDbClear()
  return new Promise((resolve, reject) => {
    const request = indexedDB.deleteDatabase(DB_NAME)
    request.onerror = () => reject(request.error ?? new Error('IndexedDB delete failed'))
    request.onsuccess = () => resolve()
  })
}
