import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test, TestInfo } from "@playwright/test";

const ADMIN_EMAIL = process.env.DEMO_ADMIN_EMAIL ?? "admin@devmark.local";
const ADMIN_PASSWORD =
  process.env.DEMO_ADMIN_PASSWORD ?? "local-demo-only-change-before-use";
const CLIENT_EMAIL =
  process.env.DEMO_CLIENT_EMAIL ?? "client@clinicafeliz.local";
const CLIENT_PASSWORD =
  process.env.DEMO_CLIENT_PASSWORD ?? "local-demo-client-only-change-before-use";

const VIEWPORTS = [
  { name: "mobile-360", width: 360, height: 800 },
  { name: "desktop-1280", width: 1280, height: 900 },
] as const;

interface EssentialRoute {
  path: string;
  heading: string;
}

const AGENCY_ROUTES: EssentialRoute[] = [
  { path: "/dashboard", heading: "Visão geral" },
  { path: "/clientes", heading: "Clientes" },
  { path: "/conteudos", heading: "Conteúdos" },
  { path: "/aprovacoes", heading: "Aprovações" },
];

const CLIENT_ROUTES: EssentialRoute[] = [
  { path: "/dashboard", heading: "Visão geral" },
  { path: "/aprovacoes", heading: "Aprovações" },
  { path: "/notificacoes", heading: "Notificações" },
];

// O script local do axe precisa ser injetado na página. A exceção à CSP fica
// restrita a este contexto de teste e não altera os headers entregues pela aplicação.
test.use({ bypassCSP: true });

async function loginThroughUi(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function waitUntilReady(page: Page, route: EssentialRoute): Promise<void> {
  await page.goto(route.path);
  await expect(
    page.getByRole("heading", { name: route.heading, exact: true }),
  ).toBeVisible();
  await expect(
    page.locator('[role="status"]').filter({
      hasText: /^(Carregando|Preparando)/,
    }),
  ).toHaveCount(0);
}

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
}

function violationSummary(
  violations: Awaited<ReturnType<AxeBuilder["analyze"]>>["violations"],
): string {
  return violations
    .map((violation) => {
      const targets = violation.nodes
        .slice(0, 5)
        .map((node) => node.target.join(" "))
        .join(", ");
      return `${violation.id} (${violation.impact ?? "impacto não informado"}): ${violation.help}. Alvos: ${targets}`;
    })
    .join("\n");
}

async function auditCurrentPage(
  page: Page,
  testInfo: TestInfo,
  viewportName: string,
  route: EssentialRoute,
): Promise<void> {
  await waitUntilReady(page, route);
  await expectNoHorizontalOverflow(page);

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  await testInfo.attach(
    `axe-${viewportName}-${route.path.replaceAll("/", "-") || "inicio"}`,
    {
      body: Buffer.from(
        JSON.stringify(
          {
            url: page.url(),
            viewport: viewportName,
            violations: results.violations,
          },
          null,
          2,
        ),
      ),
      contentType: "application/json",
    },
  );

  expect(
    results.violations,
    violationSummary(results.violations) || "Nenhuma violação WCAG 2.1 A/AA encontrada.",
  ).toEqual([]);
}

async function auditEssentialRoutes(
  page: Page,
  testInfo: TestInfo,
  routes: EssentialRoute[],
): Promise<void> {
  for (const viewport of VIEWPORTS) {
    await test.step(viewport.name, async () => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      for (const route of routes) {
        await test.step(route.path, async () => {
          await auditCurrentPage(page, testInfo, viewport.name, route);
        });
      }
    });
  }
}

test("fluxos essenciais da agência atendem WCAG 2.1 AA", async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 360, height: 800 });
  await loginThroughUi(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await auditEssentialRoutes(page, testInfo, AGENCY_ROUTES);
});

test("fluxos essenciais do cliente atendem WCAG 2.1 AA", async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 360, height: 800 });
  await loginThroughUi(page, CLIENT_EMAIL, CLIENT_PASSWORD);
  await auditEssentialRoutes(page, testInfo, CLIENT_ROUTES);
});
