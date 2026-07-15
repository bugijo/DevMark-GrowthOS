import { APIRequestContext, APIResponse, expect, request, test } from "@playwright/test";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000/api/v1";
const ADMIN_EMAIL = process.env.DEMO_ADMIN_EMAIL ?? "admin@devmark.local";
const ADMIN_PASSWORD =
  process.env.DEMO_ADMIN_PASSWORD ?? "local-demo-only-change-before-use";
const CLIENT_EMAIL = process.env.DEMO_CLIENT_EMAIL ?? "client@clinicafeliz.local";
const CLIENT_PASSWORD =
  process.env.DEMO_CLIENT_PASSWORD ?? "local-demo-client-only-change-before-use";

type LoginResponse = { csrf_token: string };
type Business = { id: string; name: string };
type Content = {
  id: string;
  business_id: string;
  status: string;
  current_version: { id: string; version_number: number; provider_name: string };
};
type Notification = { type: string; resource_id?: string };
type AuditLog = { action: string; resource_id?: string };

async function bodyOnFailure(response: APIResponse): Promise<string> {
  return response.ok() ? "" : `: ${await response.text()}`;
}

async function login(email: string, password: string): Promise<{
  context: APIRequestContext;
  csrf: string;
}> {
  const context = await request.newContext({
    baseURL: `${API_URL.replace(/\/$/, "")}/`,
  });
  const response = await context.post("auth/login", { data: { email, password } });
  expect(response.ok(), `login ${email}${await bodyOnFailure(response)}`).toBeTruthy();
  const payload = (await response.json()) as LoginResponse;
  expect(payload.csrf_token).toBeTruthy();
  return { context, csrf: payload.csrf_token };
}

function csrfHeaders(csrf: string): Record<string, string> {
  return { "X-CSRF-Token": csrf };
}

test("fluxo vertical mock gera, envia e aprova com notificação e auditoria", async () => {
  const admin = await login(ADMIN_EMAIL, ADMIN_PASSWORD);
  const client = await login(CLIENT_EMAIL, CLIENT_PASSWORD);
  try {
    const organizationResponse = await admin.context.get("organizations/current");
    expect(organizationResponse.ok()).toBeTruthy();

    const businessesResponse = await admin.context.get("businesses");
    expect(businessesResponse.ok()).toBeTruthy();
    const businesses = (await businessesResponse.json()) as Business[];
    const business = businesses.find((item) => item.name === "Clínica Veterinária Demo");
    expect(business, "o seed precisa criar a clínica fictícia").toBeTruthy();

    const brandResponse = await admin.context.put(
      `businesses/${business!.id}/brand-profile`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          brand_name: "Clínica Veterinária Demo",
          public_name: "Clínica Feliz",
          description: "Clínica fictícia usada apenas no teste automatizado.",
          segment: "Clínica veterinária",
          audience: "Tutores de animais da região",
          primary_colors: ["#1F7A6D", "#F4F1DE"],
          tone_of_voice: "acolhedor, claro e responsável",
          preferred_words: ["cuidado", "bem-estar"],
          forbidden_words: ["cura garantida"],
          slogan: "Cuidado responsável em cada fase.",
          differentiators: ["atendimento acolhedor"],
          services: ["consulta preventiva"],
          contacts: { email: "contato@clinicafeliz.local" },
          links: [],
          calls_to_action: ["Converse com nossa equipe."],
          internal_notes: "Não usar informação clínica individual.",
        },
      },
    );
    expect(brandResponse.ok(), await bodyOnFailure(brandResponse)).toBeTruthy();

    const generateResponse = await admin.context.post("contents/generate", {
      headers: csrfHeaders(admin.csrf),
      data: {
        business_id: business!.id,
        objective: "Orientar tutores sobre consulta preventiva sem aconselhamento clínico",
        channel: "INSTAGRAM",
        format: "FEED",
      },
    });
    expect(generateResponse.status(), await bodyOnFailure(generateResponse)).toBe(201);
    const generated = (await generateResponse.json()) as Content;
    expect(generated.status).toBe("DRAFT");
    expect(generated.current_version.provider_name).toBe("mock");

    const internalResponse = await admin.context.post(
      `contents/${generated.id}/submit-internal`,
      { headers: csrfHeaders(admin.csrf) },
    );
    expect(internalResponse.ok(), await bodyOnFailure(internalResponse)).toBeTruthy();
    expect(((await internalResponse.json()) as Content).status).toBe("INTERNAL_REVIEW");

    const sendResponse = await admin.context.post(
      `contents/${generated.id}/send-to-client`,
      { headers: csrfHeaders(admin.csrf) },
    );
    expect(sendResponse.ok(), await bodyOnFailure(sendResponse)).toBeTruthy();
    expect(((await sendResponse.json()) as Content).status).toBe("CLIENT_REVIEW");

    const clientNotificationsResponse = await client.context.get("notifications");
    expect(clientNotificationsResponse.ok()).toBeTruthy();
    const clientNotifications = (await clientNotificationsResponse.json()) as Notification[];
    expect(
      clientNotifications.some(
        (item) =>
          item.type === "CONTENT_REVIEW_REQUESTED" && item.resource_id === generated.id,
      ),
    ).toBeTruthy();

    const approveResponse = await client.context.post(`contents/${generated.id}/approve`, {
      headers: csrfHeaders(client.csrf),
      data: { comment: "Aprovado no cenário automatizado." },
    });
    expect(approveResponse.ok(), await bodyOnFailure(approveResponse)).toBeTruthy();
    expect(((await approveResponse.json()) as Content).status).toBe("APPROVED");

    const agencyNotificationsResponse = await admin.context.get("notifications");
    expect(agencyNotificationsResponse.ok()).toBeTruthy();
    const agencyNotifications = (await agencyNotificationsResponse.json()) as Notification[];
    expect(
      agencyNotifications.some(
        (item) => item.type === "CONTENT_DECISION" && item.resource_id === generated.id,
      ),
    ).toBeTruthy();

    const auditResponse = await admin.context.get(
      `audit-logs?business_id=${business!.id}&limit=200`,
    );
    expect(auditResponse.ok()).toBeTruthy();
    const auditLogs = (await auditResponse.json()) as AuditLog[];
    const actions = new Set(
      auditLogs.filter((item) => item.resource_id === generated.id).map((item) => item.action),
    );
    for (const action of [
      "content.generated",
      "content.submitted_internal",
      "content.sent_to_client",
      "content.approved_by_client",
    ]) {
      expect(actions.has(action), `audit log ausente: ${action}`).toBeTruthy();
    }
  } finally {
    await admin.context.dispose();
    await client.context.dispose();
  }
});

test("login funciona em viewport móvel sem rolagem horizontal", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Entre na sua conta" })).toBeVisible();
  await page.getByLabel("E-mail").fill(CLIENT_EMAIL);
  await page.getByLabel("Senha").fill(CLIENT_PASSWORD);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  expect(overflow).toBeFalsy();
});
