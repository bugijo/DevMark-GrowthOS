import {
  APIRequestContext,
  APIResponse,
  expect,
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
type Identified = { id: string };
type Strategy = {
  id: string;
  status: string;
  approved_version_id: string | null;
  current_version: { id: string; provider_name: string };
};
type ContentPlan = {
  id: string;
  content_strategy_id: string;
  strategy_version_id: string;
  status: string;
};
type CalendarEntry = {
  id: string;
  content_plan_id: string;
  content_item_id: string | null;
  visual_preset_id: string | null;
  status: string;
};
type MediaAsset = {
  id: string;
  mime_type: string;
  processing_status: string;
};
type VisualPreset = { id: string; version: number; creation_mode: string };
type Approval = { component: "TEXT" | "IMAGE"; status: string };
type Content = {
  id: string;
  status: string;
  content_strategy_id: string | null;
  strategy_version_id: string | null;
  content_plan_id: string | null;
  calendar_entry_id: string | null;
  visual_preset_id: string | null;
  published_at: string | null;
  publication_channel: string | null;
  publication_reference: string | null;
  approvals: Approval[];
  current_version: {
    id: string;
    title: string;
    provider_name: string;
    service_id: string | null;
    audience_segment_id: string | null;
    marketing_objective_id: string | null;
    visual_prompt: string;
    negative_prompt: string;
    visual_preset_snapshot: Record<string, unknown>;
    media_asset_ids: string[];
  };
};
type PeriodReport = {
  content_total: number;
  content_by_status: Record<string, number>;
  approvals_by_component: Record<string, Record<string, number>>;
  manual_publications_total: number;
  publications_by_channel: Record<string, number>;
  strategies_total: number;
  approved_strategies_total: number;
  calendar_entries_total: number;
  unavailable_metrics: string[];
};
type AuditLog = { action: string; resource_id: string | null };

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

async function login(email: string, password: string): Promise<{
  context: APIRequestContext;
  csrf: string;
}> {
  const context = await request.newContext({
    baseURL: `${API_URL.replace(/\/$/, "")}/`,
  });
  const response = await context.post("auth/login", { data: { email, password } });
  await expectStatus(response, 200, `login ${email}`);
  const payload = (await response.json()) as LoginResponse;
  expect(payload.csrf_token).toBeTruthy();
  return { context, csrf: payload.csrf_token };
}

async function loginThroughUi(
  page: import("@playwright/test").Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function expectNoHorizontalOverflow(
  page: import("@playwright/test").Page,
): Promise<void> {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
}

function csrfHeaders(csrf: string): Record<string, string> {
  return { "X-CSRF-Token": csrf };
}

function isoDate(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function shiftedUtcDate(days: number, hour = 12): Date {
  const value = new Date();
  value.setUTCHours(hour, 0, 0, 0);
  value.setUTCDate(value.getUTCDate() + days);
  return value;
}

function approvalStatuses(content: Content): Record<string, string> {
  return Object.fromEntries(
    content.approvals.map((approval) => [approval.component, approval.status]),
  );
}

test("fase 2 vincula estratégia, calendário, visual e conteúdo até relatório", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const suffix = crypto.randomUUID();
  const startsAt = shiftedUtcDate(-1);
  const endsAt = shiftedUtcDate(28);
  const scheduledAt = shiftedUtcDate(2, 15);
  const publishedAt = new Date();
  const startsOn = isoDate(startsAt);
  const endsOn = isoDate(endsAt);
  const admin = await login(ADMIN_EMAIL, ADMIN_PASSWORD);
  const reviewer = await login(CLIENT_EMAIL, CLIENT_PASSWORD);

  try {
    const businessesResponse = await admin.context.get("businesses");
    await expectStatus(businessesResponse, 200, "listar empresas");
    const businesses = (await businessesResponse.json()) as Business[];
    const business = businesses.find(
      (item) => item.name === "Clínica Veterinária Demo",
    );
    expect(business, "o seed precisa criar a clínica fictícia").toBeTruthy();
    const businessId = business!.id;

    const brandResponse = await admin.context.put(
      `businesses/${businessId}/brand-profile`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          brand_name: "Clínica Veterinária Demo",
          public_name: "Clínica Feliz",
          description: "Marca fictícia para validação ponta a ponta.",
          segment: "Clínica veterinária",
          audience: "Tutores interessados em prevenção responsável",
          primary_colors: ["#14532D", "#F7F4EA"],
          tone_of_voice: "acolhedor, claro e responsável",
          preferred_words: ["prevenção", "cuidado"],
          forbidden_words: ["cura garantida"],
          slogan: "Cuidado responsável em cada fase.",
          differentiators: ["atendimento acolhedor"],
          services: ["consulta preventiva"],
          contacts: { email: "contato@clinicafeliz.local" },
          links: [],
          calls_to_action: ["Converse com nossa equipe."],
          internal_notes: "Somente dados fictícios.",
        },
      },
    );
    await expectStatus(brandResponse, 200, "atualizar Brand Kit");

    const serviceResponse = await admin.context.post(
      `businesses/${businessId}/services`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          name: `Consulta preventiva ${suffix}`,
          description: "Serviço fictício para o fluxo E2E.",
          category: "Prevenção",
          warnings: ["Não prometer resultado clínico."],
        },
      },
    );
    await expectStatus(serviceResponse, 201, "criar serviço");
    const service = (await serviceResponse.json()) as Identified;

    const audienceResponse = await admin.context.post(
      `businesses/${businessId}/audiences`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          name: `Público prevenção ${suffix}`,
          description: "Tutores buscando orientação preventiva clara.",
          needs: ["informação confiável"],
          objections: ["receio de linguagem técnica"],
          location: "Região da clínica",
        },
      },
    );
    await expectStatus(audienceResponse, 201, "criar público");
    const audience = (await audienceResponse.json()) as Identified;

    const objectiveResponse = await admin.context.post(
      `businesses/${businessId}/objectives`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          name: `Educação preventiva ${suffix}`,
          description: "Aumentar a clareza do conteúdo.",
          planned_indicators: ["conteúdos aprovados"],
        },
      },
    );
    await expectStatus(objectiveResponse, 201, "criar objetivo");
    const objective = (await objectiveResponse.json()) as Identified;

    const mediaResponse = await admin.context.post(
      `businesses/${businessId}/media`,
      {
        headers: csrfHeaders(admin.csrf),
        multipart: {
          kind: "IMAGE",
          file: {
            name: `fase-2-${suffix}.png`,
            mimeType: "image/png",
            buffer: PNG_BYTES,
          },
        },
      },
    );
    await expectStatus(mediaResponse, 201, "enviar mídia");
    const media = (await mediaResponse.json()) as MediaAsset;
    expect(media.mime_type).toBe("image/png");
    expect(media.processing_status).toBe("READY");

    const signedMediaResponse = await admin.context.get(
      `media/${media.id}/download-url`,
    );
    await expectStatus(signedMediaResponse, 200, "emitir URL assinada da mídia");
    const signedMedia = (await signedMediaResponse.json()) as {
      url: string;
      expires_at: string;
    };
    expect(new URL(signedMedia.url).protocol).toMatch(/^https?:$/);
    expect(signedMedia.url).not.toContain(`fase-2-${suffix}`);
    expect(new Date(signedMedia.expires_at).getTime()).toBeGreaterThan(Date.now());

    const presetResponse = await admin.context.post(
      `businesses/${businessId}/visual-presets`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          name: `Preset editorial ${suffix}`,
          objective: "Educar sobre prevenção com clareza.",
          format: "FEED",
          aspect_ratio: "1:1",
          creation_mode: "HYBRID",
          color_palette: ["#14532D", "#F7F4EA"],
          fonts: ["Inter"],
          logo_media_asset_id: media.id,
          logo_position: "inferior direito",
          logo_scale_percent: 15,
          safe_margins: { top: 8, right: 8, bottom: 10, left: 8 },
          background_style: "consultório claro e organizado",
          photographic_style: "fotografia documental acolhedora",
          realism_level: "alto",
          lighting: "luz natural suave",
          composition: "animal e tutor em plano médio",
          max_text_characters: 80,
          text_rules: ["uma mensagem por peça"],
          base_prompt: "cena veterinária preventiva e acolhedora",
          negative_prompt: "ferimentos, procedimentos invasivos",
          allowed_elements: ["animais tranquilos"],
          forbidden_elements: ["ferimentos"],
          visual_signature: "formas orgânicas verdes",
          default_cta: "Converse com a equipe.",
        },
      },
    );
    await expectStatus(presetResponse, 201, "criar preset visual");
    const preset = (await presetResponse.json()) as VisualPreset;
    expect(preset.creation_mode).toBe("HYBRID");

    const promptResponse = await admin.context.post("visual-prompts/generate", {
      headers: csrfHeaders(admin.csrf),
      data: {
        business_id: businessId,
        preset_id: preset.id,
        objective: "Explicar vacinação preventiva",
        audience: "Tutores de primeira viagem",
      },
    });
    await expectStatus(promptResponse, 200, "gerar prompt visual mock");
    const prompt = (await promptResponse.json()) as {
      provider_name: string;
      prompt: string;
      negative_prompt: string;
    };
    expect(prompt.provider_name).toBe("mock");
    expect(prompt.prompt).toContain("Clínica Veterinária Demo");
    expect(prompt.negative_prompt).toContain("ferimentos");

    const strategyResponse = await admin.context.post(
      `businesses/${businessId}/strategies`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          name: `Estratégia mensal ${suffix}`,
          starts_on: startsOn,
          ends_on: endsOn,
          objective: "Educar sobre prevenção responsável.",
          positioning: "Referência local em cuidado responsável.",
          funnel: ["AWARENESS"],
          channels: ["INSTAGRAM"],
          pillars: ["prevenção"],
          planned_indicators: ["aprovações do cliente"],
          service_ids: [service.id],
          audience_ids: [audience.id],
          marketing_objective_ids: [objective.id],
        },
      },
    );
    await expectStatus(strategyResponse, 201, "criar estratégia");
    const strategy = (await strategyResponse.json()) as Strategy;
    expect(strategy.current_version.provider_name).toBe("mock");

    const strategySubmit = await admin.context.post(
      `strategies/${strategy.id}/submit-internal`,
      { headers: csrfHeaders(admin.csrf) },
    );
    await expectStatus(strategySubmit, 200, "enviar estratégia para revisão interna");
    const strategySend = await admin.context.post(
      `strategies/${strategy.id}/send-to-client`,
      { headers: csrfHeaders(admin.csrf) },
    );
    await expectStatus(strategySend, 200, "enviar estratégia ao cliente");
    expect(((await strategySend.json()) as Strategy).status).toBe("CLIENT_REVIEW");

    const strategyDecision = await reviewer.context.post(
      `strategies/${strategy.id}/decision`,
      {
        headers: csrfHeaders(reviewer.csrf),
        data: { decision: "APPROVE", comment: "Estratégia aprovada no E2E." },
      },
    );
    await expectStatus(strategyDecision, 200, "aprovar estratégia");
    const approvedStrategy = (await strategyDecision.json()) as Strategy;
    expect(approvedStrategy.status).toBe("APPROVED");
    expect(approvedStrategy.approved_version_id).toBe(strategy.current_version.id);

    const planResponse = await admin.context.post(`businesses/${businessId}/plans`, {
      headers: csrfHeaders(admin.csrf),
      data: {
        strategy_id: strategy.id,
        name: `Plano editorial ${suffix}`,
        starts_on: startsOn,
        ends_on: endsOn,
        frequency: "SEMANAL",
      },
    });
    await expectStatus(planResponse, 201, "criar plano editorial");
    const plan = (await planResponse.json()) as ContentPlan;
    expect(plan.status).toBe("ACTIVE");
    expect(plan.content_strategy_id).toBe(strategy.id);
    expect(plan.strategy_version_id).toBe(strategy.current_version.id);

    const calendarResponse = await admin.context.post(`plans/${plan.id}/entries`, {
      headers: csrfHeaders(admin.csrf),
      data: {
        title: `Vacinação preventiva ${suffix}`,
        objective: "Explicar a prevenção sem aconselhamento clínico.",
        audience: "Tutores de primeira viagem",
        channel: "INSTAGRAM",
        format: "FEED",
        suggested_for: scheduledAt.toISOString(),
        visual_preset_id: preset.id,
        notes: "Pauta fictícia validada por revisão humana.",
      },
    });
    await expectStatus(calendarResponse, 201, "criar item do calendário");
    const calendar = (await calendarResponse.json()) as CalendarEntry;
    expect(calendar.status).toBe("PLANNED");
    expect(calendar.visual_preset_id).toBe(preset.id);

    const contentResponse = await admin.context.post("contents/generate", {
      headers: csrfHeaders(admin.csrf),
      data: {
        business_id: businessId,
        objective: "Explicar a vacinação preventiva com responsabilidade.",
        channel: "INSTAGRAM",
        format: "FEED",
        content_strategy_id: strategy.id,
        strategy_version_id: strategy.current_version.id,
        content_plan_id: plan.id,
        calendar_entry_id: calendar.id,
        visual_preset_id: preset.id,
        service_id: service.id,
        audience_segment_id: audience.id,
        marketing_objective_id: objective.id,
        media_asset_id: media.id,
        notes: "Validar com profissional responsável.",
        script: "Apresentar prevenção sem promessa clínica.",
      },
    });
    await expectStatus(contentResponse, 201, "gerar conteúdo vinculado");
    const content = (await contentResponse.json()) as Content;
    expect(content.status).toBe("DRAFT");
    expect(content.content_strategy_id).toBe(strategy.id);
    expect(content.strategy_version_id).toBe(strategy.current_version.id);
    expect(content.content_plan_id).toBe(plan.id);
    expect(content.calendar_entry_id).toBe(calendar.id);
    expect(content.visual_preset_id).toBe(preset.id);
    expect(content.current_version.service_id).toBe(service.id);
    expect(content.current_version.audience_segment_id).toBe(audience.id);
    expect(content.current_version.marketing_objective_id).toBe(objective.id);
    expect(content.current_version.media_asset_ids).toContain(media.id);
    expect(content.current_version.visual_prompt).toContain(
      "Clínica Veterinária Demo",
    );
    expect(content.current_version.visual_preset_snapshot.prompt_provider).toBe("mock");

    const contentSubmit = await admin.context.post(
      `contents/${content.id}/submit-internal`,
      { headers: csrfHeaders(admin.csrf) },
    );
    await expectStatus(contentSubmit, 200, "enviar conteúdo para revisão interna");
    const contentSend = await admin.context.post(
      `contents/${content.id}/send-to-client`,
      { headers: csrfHeaders(admin.csrf) },
    );
    await expectStatus(contentSend, 200, "enviar conteúdo ao cliente");
    const sentContent = (await contentSend.json()) as Content;
    expect(sentContent.status).toBe("CLIENT_REVIEW");
    expect(approvalStatuses(sentContent)).toEqual({ IMAGE: "PENDING", TEXT: "PENDING" });

    await page.setViewportSize({ width: 360, height: 800 });
    await loginThroughUi(page, CLIENT_EMAIL, CLIENT_PASSWORD);
    await page.goto("/aprovacoes");
    const approvalCard = page.locator("article").filter({
      has: page.getByRole("heading", {
        name: sentContent.current_version.title,
        exact: true,
      }),
    });
    await expect(approvalCard).toBeVisible();
    await approvalCard
      .getByRole("button", { name: "Abrir imagem para revisar" })
      .click();
    const approvalImage = approvalCard.getByRole("img", {
      name: /Imagem em aprovação/,
    });
    await expect(approvalImage).toBeVisible();
    await expect
      .poll(() =>
        approvalImage.evaluate(
          (image: HTMLImageElement) => image.complete,
        ),
      )
      .toBe(true);
    await expect
      .poll(() =>
        approvalImage.evaluate(
          (image: HTMLImageElement) => image.naturalWidth,
        ),
      )
      .toBeGreaterThan(0);
    await expectNoHorizontalOverflow(page);

    const textDecision = await reviewer.context.post(
      `contents/${content.id}/decisions/TEXT/approve`,
      {
        headers: csrfHeaders(reviewer.csrf),
        data: { comment: "Texto aprovado no E2E." },
      },
    );
    await expectStatus(textDecision, 200, "aprovar texto");
    const textApproved = (await textDecision.json()) as Content;
    expect(textApproved.status).toBe("CLIENT_REVIEW");
    expect(approvalStatuses(textApproved)).toEqual({
      IMAGE: "PENDING",
      TEXT: "APPROVED",
    });

    const imageDecision = await reviewer.context.post(
      `contents/${content.id}/decisions/IMAGE/approve`,
      {
        headers: csrfHeaders(reviewer.csrf),
        data: { comment: "Imagem aprovada no E2E." },
      },
    );
    await expectStatus(imageDecision, 200, "aprovar imagem");
    const approvedContent = (await imageDecision.json()) as Content;
    expect(approvedContent.status).toBe("APPROVED");
    expect(approvalStatuses(approvedContent)).toEqual({
      IMAGE: "APPROVED",
      TEXT: "APPROVED",
    });

    const publicationKey = `e2e-publication-${suffix}`;
    const publicationReference = `registro-local-${suffix}`;
    const publicationResponse = await admin.context.post(
      `contents/${content.id}/publication`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          channel: "INSTAGRAM",
          published_at: publishedAt.toISOString(),
          reference: publicationReference,
          idempotency_key: publicationKey,
        },
      },
    );
    await expectStatus(publicationResponse, 200, "registrar publicação manual");
    const published = (await publicationResponse.json()) as Content;
    expect(published.status).toBe("PUBLISHED");
    expect(published.publication_channel).toBe("INSTAGRAM");
    expect(published.publication_reference).toBe(publicationReference);

    const replayResponse = await admin.context.post(
      `contents/${content.id}/publication`,
      {
        headers: csrfHeaders(admin.csrf),
        data: {
          channel: "INSTAGRAM",
          published_at: shiftedUtcDate(1).toISOString(),
          reference: "não deve substituir o registro original",
          idempotency_key: publicationKey,
        },
      },
    );
    await expectStatus(replayResponse, 200, "repetir publicação com idempotência");
    const replayed = (await replayResponse.json()) as Content;
    expect(replayed.published_at).toBe(published.published_at);
    expect(replayed.publication_reference).toBe(publicationReference);

    const calendarListResponse = await admin.context.get(
      `businesses/${businessId}/calendar?starts_on=${startsOn}&ends_on=${endsOn}`,
    );
    await expectStatus(calendarListResponse, 200, "consultar calendário");
    const calendarEntries = (await calendarListResponse.json()) as CalendarEntry[];
    const linkedEntry = calendarEntries.find((entry) => entry.id === calendar.id);
    expect(linkedEntry?.content_item_id).toBe(content.id);
    expect(linkedEntry?.status).toBe("PUBLISHED");

    const reportResponse = await admin.context.get(
      `businesses/${businessId}/reports/period?starts_on=${startsOn}&ends_on=${endsOn}`,
    );
    await expectStatus(reportResponse, 200, "consultar relatório do período");
    const report = (await reportResponse.json()) as PeriodReport;
    expect(report.content_total).toBeGreaterThanOrEqual(1);
    expect(report.content_by_status.PUBLISHED).toBeGreaterThanOrEqual(1);
    expect(report.approvals_by_component.TEXT.APPROVED).toBeGreaterThanOrEqual(1);
    expect(report.approvals_by_component.IMAGE.APPROVED).toBeGreaterThanOrEqual(1);
    expect(report.manual_publications_total).toBeGreaterThanOrEqual(1);
    expect(report.publications_by_channel.INSTAGRAM).toBeGreaterThanOrEqual(1);
    expect(report.strategies_total).toBeGreaterThanOrEqual(1);
    expect(report.approved_strategies_total).toBeGreaterThanOrEqual(1);
    expect(report.calendar_entries_total).toBeGreaterThanOrEqual(1);
    expect(report.unavailable_metrics).toContain("alcance");

    const auditResponse = await admin.context.get(
      `audit-logs?business_id=${businessId}&limit=200`,
    );
    await expectStatus(auditResponse, 200, "consultar audit trail");
    const audit = (await auditResponse.json()) as AuditLog[];
    const actions = new Set(audit.map((entry) => entry.action));
    for (const action of [
      "service.created",
      "audience_segment.created",
      "marketing_objective.created",
      "media.uploaded",
      "media.signed_url_issued",
      "visual_preset.created",
      "visual_prompt.generated",
      "strategy.created",
      "strategy.submitted_internal",
      "strategy.sent_to_client",
      "strategy.approved_by_client",
      "content_plan.created",
      "calendar_entry.created",
      "content.generated",
      "content.submitted_internal",
      "content.sent_to_client",
      "content.component_approved_by_client",
      "content.approved_by_client",
      "content.publication_recorded",
    ]) {
      expect(actions.has(action), `audit log ausente: ${action}`).toBeTruthy();
    }
    expect(
      audit.some(
        (entry) =>
          entry.action === "content.publication_recorded" &&
          entry.resource_id === content.id,
      ),
    ).toBeTruthy();
  } finally {
    await admin.context.dispose();
    await reviewer.context.dispose();
  }
});

test("áreas operacionais da fase 2 permanecem utilizáveis em 360px", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await loginThroughUi(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  for (const [path, heading] of [
    ["/marca", "Marca e presets visuais"],
    ["/planejamento", "Planejamento editorial"],
    ["/midia", "Biblioteca de mídia"],
    ["/conteudos", "Conteúdos"],
    ["/aprovacoes", "Aprovações"],
    ["/relatorios", "Relatório do período"],
  ] as const) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
    await expect(
      page.getByText(/Carregando .*…/, { exact: false }).first(),
    ).toBeHidden();
    await expectNoHorizontalOverflow(page);
  }
});
