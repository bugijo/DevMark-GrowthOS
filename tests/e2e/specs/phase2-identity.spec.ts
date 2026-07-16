import {
  APIRequestContext,
  APIResponse,
  expect,
  Page,
  request,
  test,
} from "@playwright/test";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000/api/v1";
const MAILPIT_URL = process.env.MAILPIT_URL ?? "http://127.0.0.1:8025";
const ADMIN_EMAIL = process.env.DEMO_ADMIN_EMAIL ?? "admin@devmark.local";
const ADMIN_PASSWORD =
  process.env.DEMO_ADMIN_PASSWORD ?? "local-demo-only-change-before-use";

type LoginResponse = {
  csrf_token: string;
  membership: { role: string };
};
type OrganizationInvite = {
  id: string;
  email: string;
  status: "PENDING" | "ACCEPTED" | "EXPIRED" | "REVOKED";
};
type MailpitAddress = { Address?: string; address?: string };
type MailpitSummary = {
  ID?: string;
  id?: string;
  Subject?: string;
  subject?: string;
  To?: MailpitAddress[];
  to?: MailpitAddress[];
};
type MailpitList = {
  messages?: MailpitSummary[];
  Messages?: MailpitSummary[];
};
type MailpitMessage = Record<string, unknown>;

// Tokens de uso único aparecem em URLs e corpos de requisição deste cenário.
// Desativar artefatos impede que um erro local persista esses valores.
test.use({ trace: "off", screenshot: "off" });

async function responseDetail(response: APIResponse): Promise<string> {
  return response.ok() ? "" : `: ${await response.text()}`;
}

async function expectStatus(
  response: APIResponse,
  expected: number,
  operation: string,
): Promise<void> {
  expect(
    response.status(),
    `${operation}${await responseDetail(response)}`,
  ).toBe(expected);
}

async function apiLogin(email: string, password: string): Promise<{
  context: APIRequestContext;
  csrf: string;
  payload: LoginResponse;
}> {
  const context = await request.newContext({
    baseURL: `${API_URL.replace(/\/$/, "")}/`,
  });
  const response = await context.post("auth/login", { data: { email, password } });
  await expectStatus(response, 200, `login ${email}`);
  const payload = (await response.json()) as LoginResponse;
  expect(payload.csrf_token).toBeTruthy();
  return { context, csrf: payload.csrf_token, payload };
}

function csrfHeaders(csrf: string): Record<string, string> {
  return { "X-CSRF-Token": csrf };
}

function mailpitRecipient(summary: MailpitSummary, email: string): boolean {
  const recipients = summary.To ?? summary.to ?? [];
  return recipients.some(
    (recipient) => (recipient.Address ?? recipient.address)?.toLowerCase() === email,
  );
}

function mailpitSubject(summary: MailpitSummary): string {
  return summary.Subject ?? summary.subject ?? "";
}

async function waitForMailpitMessage(
  mailpit: APIRequestContext,
  recipient: string,
  subject: string,
): Promise<MailpitMessage> {
  let summary: MailpitSummary | undefined;
  await expect
    .poll(
      async () => {
        const response = await mailpit.get("api/v1/messages?limit=100");
        if (!response.ok()) return false;
        const payload = (await response.json()) as MailpitList;
        const messages = payload.messages ?? payload.Messages ?? [];
        summary = messages.find(
          (candidate) =>
            mailpitRecipient(candidate, recipient) &&
            mailpitSubject(candidate) === subject,
        );
        return summary !== undefined;
      },
      {
        message: `aguardar e-mail local para ${recipient}`,
        timeout: 30_000,
        intervals: [250, 500, 1_000, 2_000],
      },
    )
    .toBe(true);

  const messageId = summary?.ID ?? summary?.id;
  if (!messageId) throw new Error("O serviço local não retornou o identificador da mensagem");
  const response = await mailpit.get(`api/v1/message/${encodeURIComponent(messageId)}`);
  await expectStatus(response, 200, "ler e-mail local");
  return (await response.json()) as MailpitMessage;
}

function messageText(message: MailpitMessage): string {
  return [
    message.Text,
    message.text,
    message.HTML,
    message.html,
    message.Snippet,
    message.snippet,
  ]
    .filter((value): value is string => typeof value === "string")
    .join("\n");
}

function tokenFromMessage(message: MailpitMessage, expectedPath: string): string {
  const candidates = messageText(message).match(/https?:\/\/[^\s<>"']+/g) ?? [];
  const link = candidates.find((candidate) => {
    try {
      return new URL(candidate).pathname === expectedPath;
    } catch {
      return false;
    }
  });
  if (!link) throw new Error("O e-mail local não contém o link seguro esperado");
  const token = new URL(link).hash.replace(/^#token=/, "");
  const decoded = decodeURIComponent(token);
  if (decoded.length < 32) throw new Error("O link seguro local está inválido");
  return decoded;
}

async function openFragmentRoute(page: Page, path: string, token: string): Promise<void> {
  await page.goto(`${path}#token=${encodeURIComponent(token)}`);
  await page.waitForFunction(() => window.location.hash === "", undefined, {
    timeout: 5_000,
  });
  expect(new URL(page.url()).hash).toBe("");
}

async function loginThroughUi(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  expect(overflow).toBeFalsy();
}

test("convite e recuperação usam Mailpit, fragmento e tokens de uso único", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const suffix = crypto.randomUUID();
  const invitedEmail = `e2e-${suffix}@example.test`;
  const invitedPassword = `Convite-${suffix}-A1!`;
  const resetPassword = `Redefinida-${suffix}-B2!`;
  const admin = await apiLogin(ADMIN_EMAIL, ADMIN_PASSWORD);
  const mailpit = await request.newContext({
    baseURL: `${MAILPIT_URL.replace(/\/$/, "")}/`,
  });
  const security = await request.newContext({
    baseURL: `${API_URL.replace(/\/$/, "")}/`,
  });
  let invitedSession: APIRequestContext | undefined;
  let resetSession: APIRequestContext | undefined;

  try {
    const inviteResponse = await admin.context.post("members/invitations", {
      headers: csrfHeaders(admin.csrf),
      data: {
        name: `Pessoa E2E ${suffix}`,
        email: invitedEmail,
        role: "STRATEGIST",
        business_id: null,
      },
    });
    await expectStatus(inviteResponse, 201, "criar convite seguro");
    const invitation = (await inviteResponse.json()) as OrganizationInvite;
    expect(invitation.email).toBe(invitedEmail);
    expect(invitation.status).toBe("PENDING");

    const invitationMail = await waitForMailpitMessage(
      mailpit,
      invitedEmail,
      "Seu convite para o DevMark GrowthOS",
    );
    const invitationToken = tokenFromMessage(invitationMail, "/convites/aceitar");

    await page.setViewportSize({ width: 360, height: 800 });
    await openFragmentRoute(page, "/convites/aceitar", invitationToken);
    await expect(
      page.getByRole("heading", { name: "Entrar para a organização" }),
    ).toBeVisible();
    await expect(page.getByLabel(/^Seu nome/)).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.getByLabel(/^Seu nome/).fill(`Pessoa E2E ${suffix}`);
    await page.getByLabel(/^Crie uma senha/).fill(invitedPassword);
    await page.getByLabel(/^Confirme a senha/).fill(invitedPassword);
    await page.getByRole("button", { name: "Aceitar convite", exact: true }).click();
    await expect(page.getByText("Convite aceito. Seu acesso já está ativo.")).toBeVisible();

    const usedInvitation = await security.post("auth/invitations/inspect", {
      data: { token: invitationToken },
    });
    await expectStatus(usedInvitation, 400, "rejeitar convite já utilizado");

    const invitationsResponse = await admin.context.get("members/invitations");
    await expectStatus(invitationsResponse, 200, "consultar convites");
    const invitations = (await invitationsResponse.json()) as OrganizationInvite[];
    expect(
      invitations.find((candidate) => candidate.id === invitation.id)?.status,
    ).toBe("ACCEPTED");

    const invitedLogin = await apiLogin(invitedEmail, invitedPassword);
    invitedSession = invitedLogin.context;
    expect(invitedLogin.payload.membership.role).toBe("STRATEGIST");

    const recoveryResponse = await security.post("auth/password-recovery", {
      data: { email: invitedEmail },
    });
    await expectStatus(recoveryResponse, 202, "solicitar recuperação de senha");
    const recoveryPayload = (await recoveryResponse.json()) as { message: string };
    expect(recoveryPayload.message).toContain("Se o e-mail estiver cadastrado");

    const resetMail = await waitForMailpitMessage(
      mailpit,
      invitedEmail,
      "Redefinição de senha do DevMark GrowthOS",
    );
    const resetToken = tokenFromMessage(resetMail, "/redefinir-senha");

    await openFragmentRoute(page, "/redefinir-senha", resetToken);
    await expect(page.getByRole("heading", { name: "Criar nova senha" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.getByLabel(/^Nova senha/).fill(resetPassword);
    await page.getByLabel(/^Confirme a nova senha/).fill(resetPassword);
    await page.getByRole("button", { name: "Salvar nova senha", exact: true }).click();
    await expect(page.getByText("Senha redefinida com sucesso.")).toBeVisible();

    const reusedReset = await security.post("auth/password-reset", {
      data: { token: resetToken, new_password: `Outra-${suffix}-C3!` },
    });
    await expectStatus(reusedReset, 400, "rejeitar redefinição já utilizada");

    const invalidatedSession = await invitedSession.get("auth/me");
    await expectStatus(
      invalidatedSession,
      401,
      "invalidar sessão anterior à redefinição",
    );
    const oldPasswordContext = await request.newContext({
      baseURL: `${API_URL.replace(/\/$/, "")}/`,
    });
    const oldPasswordLogin = await oldPasswordContext.post("auth/login", {
      data: { email: invitedEmail, password: invitedPassword },
    });
    await expectStatus(oldPasswordLogin, 401, "rejeitar senha anterior");
    await oldPasswordContext.dispose();

    const resetLogin = await apiLogin(invitedEmail, resetPassword);
    resetSession = resetLogin.context;
    expect(resetLogin.payload.membership.role).toBe("STRATEGIST");
  } finally {
    await invitedSession?.dispose();
    await resetSession?.dispose();
    await security.dispose();
    await mailpit.dispose();
    await admin.context.dispose();
  }
});

test("gestão de equipe não cria overflow em viewport de 360px", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await loginThroughUi(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.goto("/equipe");
  await expect(page.getByRole("heading", { name: "Equipe", exact: true })).toBeVisible();
  await expect(page.getByText("Carregando equipe e convites…", { exact: true })).toBeHidden();
  await expect(page.getByRole("heading", { name: "Convidar uma pessoa" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});
