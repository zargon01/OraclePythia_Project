const BACKEND_URL =
  import.meta.env.VITE_API_BASE || import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export async function sendChat({ type, query, current_code }) {
  const res = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      type,
      query,
      current_code: current_code ?? "",
    }),
  });

  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const message = data?.detail || data?.raw || "Request failed";
    throw new Error(message);
  }

  return data;
}