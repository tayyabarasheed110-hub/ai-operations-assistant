/**
 * Verifies Vite proxy target (backend) responds. Run with backend on :8000.
 * Usage: node scripts/check-backend-connection.mjs [baseUrl]
 */
const base = process.argv[2] || "http://127.0.0.1:8000";

async function main() {
  const health = await fetch(`${base}/health`);
  if (!health.ok) {
    console.error("FAIL: /health", health.status);
    process.exit(1);
  }
  const signIn = await fetch(`${base}/api/auth/sign-in`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "ali@assistant.test", password: "DemoPass123!" }),
  });
  if (!signIn.ok) {
    console.error("FAIL: sign-in (seed DB?)", signIn.status, await signIn.text());
    process.exit(1);
  }
  const cookie = signIn.headers.get("set-cookie");
  const me = await fetch(`${base}/api/auth/me`, {
    headers: cookie ? { Cookie: cookie.split(";")[0] } : {},
  });
  if (!me.ok) {
    console.error("FAIL: /api/auth/me", me.status);
    process.exit(1);
  }
  const profile = await me.json();
  console.log("OK: backend reachable, auth cookie + /me works for", profile.email);
}

main().catch((e) => {
  console.error("FAIL:", e.message);
  process.exit(1);
});
