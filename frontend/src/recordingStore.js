// Persist recording chunks immediately so a tab crash does not lose the meeting.
function database() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('meet-iq-recording', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('chunks', { autoIncrement: true });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function transaction(mode, action) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('chunks', mode);
    const request = action(tx.objectStore('chunks'));
    tx.oncomplete = () => { db.close(); resolve(request.result); };
    tx.onerror = () => { db.close(); reject(tx.error); };
    tx.onabort = () => { db.close(); reject(tx.error || new Error('Recording storage failed')); };
  });
}
export const saveChunk = blob => transaction('readwrite', store => store.add(blob));
export const clearRecording = () => transaction('readwrite', store => store.clear());
export const recordingExists = () => transaction('readonly', store => store.count());
export async function restoreRecording() {
  const chunks = await transaction('readonly', store => store.getAll());
  if (!chunks.length) return null;
  const type = chunks[0].type || 'audio/webm';
  const extension = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm';
  return new File(chunks, `meeting-recording.${extension}`, { type });
}
