import { APIRequestContext, expect, request, test } from "@playwright/test";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000/api/v1";
const ADMIN_EMAIL = process.env.DEMO_ADMIN_EMAIL ?? "admin@devmark.local";
const ADMIN_PASSWORD =
  process.env.DEMO_ADMIN_PASSWORD ?? "local-demo-only-change-before-use";

type Generation = {
  id: string;
  provider: string;
  simulated: boolean;
  used_fallback: boolean;
  requires_approval: boolean;
  can_publish_automatically: boolean;
  alternatives: Array<{ payload: { title?: string } }>;
};

async function login(): Promise<{ context: APIRequestContext; csrf: string }> {
  const context = await request.newContext({
    baseURL: `${API_URL.replace(/\/$/, "")}/`,
  });
  const response = await context.post("auth/login", {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  });
  expect(response.status()).toBe(200);
  const payload = (await response.json()) as { csrf_token: string };
  return { context, csrf: payload.csrf_token };
}

test("Growth Agent funciona offline com mock e sem publicação automática", async () => {
  const admin = await login();
  try {
    const businessesResponse = await admin.context.get("businesses");
    expect(businessesResponse.status()).toBe(200);
    const businesses = (await businessesResponse.json()) as Array<{ id: string }>;
    expect(businesses.length).toBeGreaterThan(0);

    const response = await admin.context.post(
      `businesses/${businesses[0].id}/ai/generations`,
      {
        headers: { "X-CSRF-Token": admin.csrf },
        data: {
          task: "CONTENT_IDEAS",
          instruction: "Gere ideias responsáveis para revisão humana",
          alternatives: 3,
        },
      },
    );
    const responseText = await response.text();
    expect(response.status(), responseText).toBe(201);
    const generation = JSON.parse(responseText) as Generation;
    expect(generation.provider).toBe("mock");
    expect(generation.simulated).toBe(true);
    expect(generation.requires_approval).toBe(true);
    expect(generation.can_publish_automatically).toBe(false);
    expect(generation.alternatives).toHaveLength(3);
  } finally {
    await admin.context.dispose();
  }
});
