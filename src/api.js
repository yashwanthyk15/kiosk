const API_BASE = import.meta.env.VITE_API_URL || "";

export async function startSession(sceneKey = "order", language = "kn") {
  const query = new URLSearchParams({ scene_key: sceneKey, language });
  const response = await fetch(`${API_BASE}/api/session?${query}`, { method: "POST" });
  if (!response.ok) throw new Error("Could not start an order. Check that the ordering server is running.");
  return response.json();
}

export function socketUrl(sessionId) {
  const base = API_BASE || window.location.origin;
  const url = new URL(`/ws/session/${sessionId}`, base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function voiceUrl(lineKey, lineText, language = "kn") {
  let version = 2166136261;
  for (let index = 0; index < lineText.length; index += 1) {
    version ^= lineText.charCodeAt(index);
    version = Math.imul(version, 16777619);
  }
  const query = new URLSearchParams({
    language,
    v: (version >>> 0).toString(16),
  });
  return `${API_BASE}/api/voice/${encodeURIComponent(lineKey)}?${query}`;
}
