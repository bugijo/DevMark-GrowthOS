import {
  APIRequestContext,
  APIResponse,
  expect,
  Page,
  request,
  test,
} from "@playwright/test";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000/api/v1";
const ADMIN_EMAIL = process.env.DEMO_ADMIN_EMAIL ?? "admin@devmark.local";
const ADMIN_PASSWORD =
  process.env.DEMO_ADMIN_PASSWORD ?? "local-demo-only-change-before-use";
const CLIENT_EMAIL = process.env.DEMO_CLIENT_EMAIL ?? "client@clinicafeliz.local";
const CLIENT_PASSWORD =
  process.env.DEMO_CLIENT_PASSWORD ?? "local-demo-client-only-change-before-use";
const PNG_BYTES = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

type LoginResponse = { csrf_token: string };
type Business = { id: string; name: string };
type MediaAsset = { id: string; display_name: string };
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

async function loginThroughUi(page: Page, email: string, password: string) {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Entre na sua conta" })).toBeVisible();
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Visão geral" })).toBeVisible();
}

async function logoutThroughUi(page: Page) {
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Entre na sua conta" })).toBeVisible();
}

async function markExistingNotificationsAsRead(page: Page) {
  await page.getByRole("link", { name: "Notificações", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Notificações" })).toBeVisible();
  await expect(page.getByText("Carregando notificações…", { exact: true })).toBeHidden();

  const unreadButtons = page.getByRole("button", { name: "Marcar como lida" });
  let unreadCount = await unreadButtons.count();
  while (unreadCount > 0) {
    await unreadButtons.first().click();
    unreadCount -= 1;
    await expect(unreadButtons).toHaveCount(unreadCount);
  }
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

    const mediaResponse = await admin.context.post(
      `businesses/${business!.id}/media`,
      {
        headers: csrfHeaders(admin.csrf),
        multipart: {
          kind: "IMAGE",
          file: {
            name: "fluxo-vertical.png",
            mimeType: "image/png",
            buffer: PNG_BYTES,
          },
        },
      },
    );
    expect(mediaResponse.status(), await bodyOnFailure(mediaResponse)).toBe(201);
    const media = (await mediaResponse.json()) as MediaAsset;

    const generateResponse = await admin.context.post("contents/generate", {
      headers: csrfHeaders(admin.csrf),
      data: {
        business_id: business!.id,
        objective: "Orientar tutores sobre consulta preventiva sem aconselhamento clínico",
        channel: "INSTAGRAM",
        format: "FEED",
        media_asset_id: media.id,
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

    const textApprovalResponse = await client.context.post(
      `contents/${generated.id}/decisions/TEXT/approve`,
      {
        headers: csrfHeaders(client.csrf),
        data: { comment: "Texto aprovado no cenário automatizado." },
      },
    );
    expect(
      textApprovalResponse.ok(),
      await bodyOnFailure(textApprovalResponse),
    ).toBeTruthy();
    expect(((await textApprovalResponse.json()) as Content).status).toBe(
      "CLIENT_REVIEW",
    );
    const approveResponse = await client.context.post(
      `contents/${generated.id}/decisions/IMAGE/approve`,
      {
        headers: csrfHeaders(client.csrf),
        data: { comment: "Imagem aprovada no cenário automatizado." },
      },
    );
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

test("fluxo vertical completo funciona pela interface da agência e do cliente", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const objective = `Fluxo UI E2E ${crypto.randomUUID()}: orientar sobre consulta preventiva`;
  const setupAdmin = await login(ADMIN_EMAIL, ADMIN_PASSWORD);
  let setupBusinessId: string | undefined;
  let setupMedia: MediaAsset | undefined;
  try {
    const businessesResponse = await setupAdmin.context.get("businesses");
    expect(businessesResponse.ok()).toBeTruthy();
    const businesses = (await businessesResponse.json()) as Business[];
    const business = businesses.find(
      (item) => item.name === "Clínica Veterinária Demo",
    );
    expect(business).toBeTruthy();
    setupBusinessId = business!.id;
    const mediaResponse = await setupAdmin.context.post(
      `businesses/${business!.id}/media`,
      {
        headers: csrfHeaders(setupAdmin.csrf),
        multipart: {
          kind: "IMAGE",
          file: {
            name: `fluxo-ui-${crypto.randomUUID()}.png`,
            mimeType: "image/png",
            buffer: PNG_BYTES,
          },
        },
      },
    );
    expect(mediaResponse.status(), await bodyOnFailure(mediaResponse)).toBe(201);
    setupMedia = (await mediaResponse.json()) as MediaAsset;
  } finally {
    await setupAdmin.context.dispose();
  }
  expect(setupBusinessId).toBeTruthy();
  expect(setupMedia).toBeTruthy();

  await loginThroughUi(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await markExistingNotificationsAsRead(page);

  await page.getByRole("link", { name: "Conteúdos", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Conteúdos" })).toBeVisible();
  await expect(page.getByText("Carregando conteúdos…", { exact: true })).toBeHidden();
  await expect(page.getByLabel(/^Cliente/)).toHaveValue(setupBusinessId!);
  await page.getByLabel("Imagem principal").selectOption(setupMedia!.id);
  await page.getByLabel("Objetivo do conteúdo").fill(objective);

  const generatedResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname.endsWith("/api/v1/contents/generate"),
  );
  await page.getByRole("button", { name: "Gerar rascunho" }).click();
  const generatedResponse = await generatedResponsePromise;
  expect(
    generatedResponse.ok(),
    generatedResponse.ok() ? "" : await generatedResponse.text(),
  ).toBeTruthy();
  const generated = (await generatedResponse.json()) as Content;

  const agencyCard = page
    .locator("article")
    .filter({ has: page.getByText(objective, { exact: true }) });
  await expect(agencyCard).toHaveCount(1);
  await expect(agencyCard.getByText("Rascunho", { exact: true })).toBeVisible();
  await agencyCard
    .getByRole("button", { name: "Enviar para revisão interna" })
    .click();
  await expect(agencyCard.getByText("Revisão interna", { exact: true })).toBeVisible();
  await agencyCard
    .getByRole("button", { name: "Enviar texto e imagem ao cliente", exact: true })
    .click();
  await expect(agencyCard.getByText("Aguardando cliente", { exact: true })).toBeVisible();

  await logoutThroughUi(page);
  await loginThroughUi(page, CLIENT_EMAIL, CLIENT_PASSWORD);
  await page.getByRole("link", { name: "Aprovações", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Aprovações" })).toBeVisible();
  await expect(page.getByText("Carregando aprovações…", { exact: true })).toBeHidden();

  const clientCard = page
    .locator("article")
    .filter({ has: page.getByText(objective, { exact: true }) });
  await expect(clientCard).toHaveCount(1);
  await clientCard
    .getByRole("button", { name: "Abrir imagem para revisar" })
    .click();
  await expect(clientCard.getByRole("img", { name: /Imagem em aprovação/ })).toBeVisible();
  await clientCard.getByRole("button", { name: "Aprovar texto" }).click();
  await expect(
    page.getByText(/Texto aprovado\. O conteúdo só avança/, { exact: true }),
  ).toBeVisible();
  await clientCard.getByRole("button", { name: "Aprovar imagem" }).click();
  await expect(
    page.getByText(/Imagem aprovada\. O conteúdo só avança/, { exact: true }),
  ).toBeVisible();
  await expect(clientCard.getByText("Aprovado", { exact: true }).first()).toBeVisible();

  await logoutThroughUi(page);
  await loginThroughUi(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.getByRole("link", { name: "Notificações", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Notificações" })).toBeVisible();
  await expect(page.getByText("Carregando notificações…", { exact: true })).toBeHidden();
  await page.getByRole("button", { name: /^Não lidas \(/ }).click();

  const decisionNotification = page.getByRole("listitem").filter({
    has: page.getByRole("heading", { name: "Conteúdo aprovado", exact: true }),
  });
  await expect(decisionNotification).toHaveCount(1);
  await expect(decisionNotification.getByText("Nova", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Registros", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Registros de atividade" }),
  ).toBeVisible();
  await expect(page.getByText("Carregando registros…", { exact: true })).toBeHidden();

  for (const actionLabel of [
    "Conteúdo gerado",
    "Enviado para revisão interna",
    "Enviado para o cliente",
    "Aprovado pelo cliente",
  ]) {
    const auditEvent = page
      .getByRole("listitem")
      .filter({ hasText: generated.id })
      .filter({
        has: page.getByRole("heading", { name: actionLabel, exact: true }),
      });
    await expect(auditEvent, `registro de auditoria ausente: ${actionLabel}`).toHaveCount(1);
  }
});
