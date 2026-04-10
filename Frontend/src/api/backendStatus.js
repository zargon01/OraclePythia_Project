const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export async function checkBackendStatus() {
  const res = await fetch(`${BACKEND_URL}/`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Backend not reachable");
  }

  const data = await res.json();

  return data?.status === "running";
}