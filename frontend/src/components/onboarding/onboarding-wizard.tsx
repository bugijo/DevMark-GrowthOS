"use client";

import Link from "next/link";
import {
  FormEvent,
  type Dispatch,
  type SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  OnboardingStepFields,
  type OnboardingResources,
} from "@/components/onboarding/onboarding-steps";
import { Button } from "@/components/ui/button";
import { Alert, LoadingState } from "@/components/ui/feedback";
import { Card, PageHeader } from "@/components/ui/page";
import { useAuth } from "@/contexts/auth-context";
import { ApiError, api } from "@/lib/api";
import {
  buildOnboardingStepPayload,
  createOnboardingFormState,
  ONBOARDING_STEPS,
  type OnboardingFormState,
  type StepValidationErrors,
  validateOnboardingStep,
} from "@/lib/onboarding";
import type { Business, BusinessOnboarding } from "@/types/api";

const emptyResources: OnboardingResources = {
  media: [],
  approvers: [],
  presets: [],
};

function requestMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function mergeSavedStep(
  current: OnboardingFormState,
  saved: OnboardingFormState,
  step: number,
): OnboardingFormState {
  switch (step) {
    case 1:
      return { ...current, company: saved.company };
    case 2:
      return { ...current, segment: saved.segment };
    case 3:
      return { ...current, services: saved.services };
    case 4:
      return { ...current, audiences: saved.audiences };
    case 5:
      return { ...current, objectives: saved.objectives };
    case 6:
      return { ...current, differentiators: saved.differentiators };
    case 7:
      return { ...current, tone: saved.tone };
    case 8:
      return { ...current, logoIds: saved.logoIds };
    case 9:
      return { ...current, visual: saved.visual };
    case 10:
      return { ...current, referenceIds: saved.referenceIds };
    case 11:
      return { ...current, rules: saved.rules };
    case 12:
      return { ...current, approverIds: saved.approverIds };
    case 13:
      return { ...current, notifications: saved.notifications };
    case 14:
      return { ...current, preset: saved.preset };
    case 15:
      return { ...current, review: saved.review };
    default:
      return current;
  }
}

function completedLabel(onboarding: BusinessOnboarding): string {
  if (!onboarding.completed_at) return "Concluído";
  return `Concluído em ${new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(onboarding.completed_at))}`;
}

export function OnboardingWizard({ businessId }: { businessId: string }) {
  const { activeOrganizationId, roles } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [onboarding, setOnboarding] = useState<BusinessOnboarding | null>(null);
  const [formState, setFormState] = useState<OnboardingFormState | null>(null);
  const [resources, setResources] = useState<OnboardingResources>(emptyResources);
  const [activeStep, setActiveStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [validationErrors, setValidationErrors] = useState<StepValidationErrors>({});
  const [dirtySteps, setDirtySteps] = useState<Set<number>>(new Set());
  const [editingCompleted, setEditingCompleted] = useState(false);

  const loadResources = useCallback(async () => {
    const [mediaResult, approversResult, presetsResult] = await Promise.allSettled([
      api.media.list(businessId),
      api.onboarding.approvers(businessId),
      api.catalogs.presets.list(businessId),
    ]);
    setResources({
      media: mediaResult.status === "fulfilled" ? mediaResult.value : [],
      approvers:
        approversResult.status === "fulfilled" ? approversResult.value : [],
      presets: presetsResult.status === "fulfilled" ? presetsResult.value : [],
      mediaError:
        mediaResult.status === "rejected"
          ? requestMessage(mediaResult.reason, "Não foi possível carregar a mídia.")
          : undefined,
      membersError:
        approversResult.status === "rejected"
          ? requestMessage(
              approversResult.reason,
              "Não foi possível carregar as pessoas responsáveis.",
            )
          : undefined,
      presetsError:
        presetsResult.status === "rejected"
          ? requestMessage(presetsResult.reason, "Não foi possível carregar os presets.")
          : undefined,
    });
  }, [businessId]);

  const load = useCallback(
    async () => {
      if (!activeOrganizationId) return;
      setLoading(true);
      setError(null);
      setSuccess(null);
      setConflict(false);
      try {
        const nextBusiness = await api.businesses.get(businessId);
        let nextOnboarding: BusinessOnboarding;
        try {
          nextOnboarding = await api.onboarding.get(businessId);
        } catch (onboardingError) {
          if (onboardingError instanceof ApiError && onboardingError.status === 404) {
            nextOnboarding = await api.onboarding.start(businessId);
          } else {
            throw onboardingError;
          }
        }
        setBusiness(nextBusiness);
        setOnboarding(nextOnboarding);
        setEditingCompleted(false);
        setFormState(createOnboardingFormState(nextBusiness, nextOnboarding));
        setDirtySteps(new Set());
        setActiveStep(nextOnboarding.status === "COMPLETED" ? 15 : nextOnboarding.current_step);
        await loadResources();
      } catch (requestError) {
        setError(requestMessage(requestError, "Não foi possível abrir o onboarding."));
      } finally {
        setLoading(false);
      }
    }, [activeOrganizationId, businessId, loadResources],
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setValidationErrors({});
    setError(null);
    const heading = document.getElementById("onboarding-step-title");
    heading?.focus();
  }, [activeStep]);

  const allowedSteps = useMemo(() => {
    if (!onboarding) return new Set([1]);
    return new Set([
      ...onboarding.completed_steps,
      onboarding.current_step,
      activeStep,
    ]);
  }, [activeStep, onboarding]);
  const canUpload = roles.some((role) =>
    ["SUPER_ADMIN", "AGENCY_ADMIN"].includes(role),
  );

  async function saveStep(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!formState || !onboarding || !business) return;
    const nextErrors = validateOnboardingStep(activeStep, formState);
    setValidationErrors(nextErrors);
    setError(null);
    setSuccess(null);
    setConflict(false);
    if (Object.keys(nextErrors).length > 0) return;

    const wasCompleted = onboarding.status === "COMPLETED";
    setSaving(true);
    try {
      const saved = await api.onboarding.saveStep(
        businessId,
        buildOnboardingStepPayload(activeStep, onboarding.revision, formState),
      );
      const localBusiness: Business = {
        ...business,
        name: activeStep === 1 ? formState.company.name.trim() : business.name,
        segment: activeStep === 2 ? formState.segment.trim() : business.segment,
      };
      const persisted = createOnboardingFormState(localBusiness, saved);
      setBusiness(localBusiness);
      setOnboarding(saved);
      setFormState((current) => {
        const merged = current
          ? mergeSavedStep(current, persisted, activeStep)
          : persisted;
        return wasCompleted ? { ...merged, review: persisted.review } : merged;
      });
      setSuccess(
        wasCompleted
          ? `Etapa ${activeStep} salva. Faça uma nova revisão final antes de concluir.`
          : `Etapa ${activeStep} salva com segurança.`,
      );
      setDirtySteps((current) => {
        const next = new Set(current);
        next.delete(activeStep);
        return next;
      });
      if (activeStep === 14) await loadResources();
      if (wasCompleted) {
        setEditingCompleted(false);
        setActiveStep(15);
      } else if (activeStep < ONBOARDING_STEPS.length) {
        setActiveStep(activeStep + 1);
      }
    } catch (requestError) {
      const isConflict = requestError instanceof ApiError && requestError.status === 409;
      setConflict(isConflict);
      setError(
        requestMessage(
          requestError,
          isConflict
            ? "Este onboarding foi atualizado em outra sessão."
            : "Não foi possível salvar esta etapa.",
        ),
      );
    } finally {
      setSaving(false);
    }
  }

  async function complete() {
    if (!onboarding) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    setConflict(false);
    try {
      const completed = await api.onboarding.complete(businessId, onboarding.revision);
      setOnboarding(completed);
      setSuccess("Onboarding concluído. A operação já pode usar estes dados.");
    } catch (requestError) {
      const isConflict = requestError instanceof ApiError && requestError.status === 409;
      setConflict(isConflict);
      setError(requestMessage(requestError, "Não foi possível concluir o onboarding."));
    } finally {
      setSaving(false);
    }
  }

  async function uploadAsset(file: File) {
    setUploading(true);
    setError(null);
    try {
      const asset = await api.media.upload(businessId, file);
      setResources((current) => ({ ...current, media: [asset, ...current.media] }));
      setFormState((current) => {
        if (!current) return current;
        if (activeStep === 8) {
          return { ...current, logoIds: Array.from(new Set([...current.logoIds, asset.id])) };
        }
        if (activeStep === 10) {
          return {
            ...current,
            referenceIds: Array.from(new Set([...current.referenceIds, asset.id])),
          };
        }
        return current;
      });
      setDirtySteps((current) => new Set(current).add(activeStep));
      setSuccess("Imagem enviada e selecionada nesta etapa.");
    } catch (requestError) {
      setError(requestMessage(requestError, "Não foi possível enviar a imagem."));
    } finally {
      setUploading(false);
    }
  }

  if (loading) return <LoadingState label="Abrindo o onboarding do cliente…" />;

  if (error && (!business || !onboarding || !formState)) {
    return (
      <div className="space-y-4">
        <Alert>{error}</Alert>
        <Button onClick={() => void load()}>Tentar novamente</Button>
      </div>
    );
  }

  if (!business || !onboarding || !formState) return null;

  if (onboarding.status === "COMPLETED" && !editingCompleted) {
    return (
      <>
        <PageHeader
          eyebrow="Onboarding"
          title={business.name}
          description="O cadastro operacional deste cliente está completo e pode ser revisado a qualquer momento."
          action={
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                onClick={() => {
                  setEditingCompleted(true);
                  setActiveStep(15);
                }}
              >
                Editar onboarding
              </Button>
              <Link href={`/clientes/${businessId}`} className="inline-flex min-h-11 items-center rounded-xl border border-slate-300 bg-white px-4 text-sm font-bold text-slate-800 hover:bg-slate-50">
                Abrir Brand Kit
              </Link>
            </div>
          }
        />
        {success ? <Alert tone="success">{success}</Alert> : null}
        <Card>
          <div className="flex size-12 items-center justify-center rounded-full bg-emerald-100 text-xl font-black text-emerald-800" aria-hidden="true">✓</div>
          <h2 className="mt-4 text-xl font-bold text-slate-950">Onboarding completo</h2>
          <p className="mt-1 text-sm text-slate-600">{completedLabel(onboarding)}</p>
          <dl className="mt-5 grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-3">
            <div><dt className="text-slate-500">Serviços</dt><dd className="text-lg font-bold">{onboarding.summary.service_ids.length}</dd></div>
            <div><dt className="text-slate-500">Públicos</dt><dd className="text-lg font-bold">{onboarding.summary.audience_ids.length}</dd></div>
            <div><dt className="text-slate-500">Objetivos</dt><dd className="text-lg font-bold">{onboarding.summary.objective_ids.length}</dd></div>
            <div><dt className="text-slate-500">Logos</dt><dd className="text-lg font-bold">{onboarding.summary.logo_media_asset_ids.length}</dd></div>
            <div><dt className="text-slate-500">Referências</dt><dd className="text-lg font-bold">{onboarding.summary.visual_reference_media_asset_ids.length}</dd></div>
            <div><dt className="text-slate-500">Aprovadores</dt><dd className="text-lg font-bold">{onboarding.summary.approver_membership_ids.length}</dd></div>
          </dl>
        </Card>
      </>
    );
  }

  const canComplete =
    onboarding.status !== "COMPLETED" &&
    onboarding.completed_steps.includes(15) &&
    onboarding.missing_steps.length === 0 &&
    dirtySteps.size === 0;
  const persistedReview = onboarding.step_data["15"] ?? {};
  const reviewMatchesSaved =
    persistedReview.confirmed === formState.review.confirmed &&
    persistedReview.notes === formState.review.notes.trim();
  const setDirtyFormState: Dispatch<SetStateAction<OnboardingFormState | null>> =
    (value) => {
      setDirtySteps((current) => new Set(current).add(activeStep));
      setFormState(value);
    };

  return (
    <>
      <PageHeader
        eyebrow="Configuração guiada"
        title={`Onboarding · ${business.name}`}
        description={
          editingCompleted
            ? "Edite uma etapa por vez. Cada alteração salva mantém o onboarding concluído."
            : "Cada avanço é salvo no servidor. Você pode sair e continuar depois sem recomeçar."
        }
        action={
          editingCompleted ? (
            <Button type="button" variant="secondary" onClick={() => setEditingCompleted(false)}>
              Voltar ao resumo
            </Button>
          ) : (
            <Link href={`/clientes/${businessId}`} className="inline-flex min-h-11 items-center rounded-xl border border-slate-300 bg-white px-4 text-sm font-bold text-slate-800 hover:bg-slate-50">
              Voltar ao cliente
            </Link>
          )
        }
      />

      <Card className="space-y-3">
        <div className="flex items-center justify-between gap-4 text-sm">
          <span className="font-bold text-slate-800">Progresso salvo</span>
          <span className="font-black text-emerald-800">{onboarding.progress_percent}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Progresso do onboarding" aria-valuemin={0} aria-valuemax={100} aria-valuenow={onboarding.progress_percent}>
          <div className="h-full rounded-full bg-emerald-700 transition-[width]" style={{ width: `${onboarding.progress_percent}%` }} />
        </div>
        <p className="text-xs text-slate-500">{onboarding.completed_steps.length} de {ONBOARDING_STEPS.length} etapas salvas</p>
      </Card>

      <div className="grid items-start gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <Card className="lg:sticky lg:top-5">
          <label htmlFor="onboarding-step-select" className="text-sm font-bold text-slate-800 lg:hidden">Ir para uma etapa disponível</label>
          <select
            id="onboarding-step-select"
            value={activeStep}
            onChange={(event) => setActiveStep(Number(event.target.value))}
            className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm lg:hidden"
          >
            {ONBOARDING_STEPS.map((label, index) => {
              const step = index + 1;
              return allowedSteps.has(step) ? <option key={label} value={step}>{step}. {label}</option> : null;
            })}
          </select>
          <ol className="hidden space-y-1 lg:block" aria-label="Etapas do onboarding">
            {ONBOARDING_STEPS.map((label, index) => {
              const step = index + 1;
              const completed = onboarding.completed_steps.includes(step);
              const allowed = allowedSteps.has(step);
              return (
                <li key={label}>
                  <button
                    type="button"
                    disabled={!allowed}
                    aria-current={activeStep === step ? "step" : undefined}
                    onClick={() => setActiveStep(step)}
                    className={`flex min-h-10 w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-sm ${activeStep === step ? "bg-emerald-50 font-bold text-emerald-900" : allowed ? "text-slate-700 hover:bg-slate-50" : "cursor-not-allowed text-slate-400"}`}
                  >
                    <span className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-black ${completed ? "bg-emerald-700 text-white" : "bg-slate-100 text-slate-600"}`} aria-hidden="true">
                      {completed ? "✓" : step}
                    </span>
                    <span>{label}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </Card>

        <Card>
          {error ? <div className="mb-5"><Alert>{error}</Alert></div> : null}
          {conflict ? (
            <div className="mb-5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-bold">Há uma versão mais recente no servidor.</p>
              <p className="mt-1">Recarregue antes de salvar novamente para não sobrescrever o trabalho de outra pessoa.</p>
              <Button type="button" variant="secondary" className="mt-3" onClick={() => void load()}>Recarregar versão do servidor</Button>
            </div>
          ) : null}
          {success ? <div className="mb-5"><Alert tone="success">{success}</Alert></div> : null}

          <form onSubmit={saveStep} noValidate>
            <OnboardingStepFields
              step={activeStep}
              state={formState}
              setState={setDirtyFormState}
              errors={validationErrors}
              resources={resources}
              uploading={uploading}
              allowUpload={canUpload}
              uploadAsset={uploadAsset}
            />

            <div className="mt-8 flex flex-col-reverse gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <Button
                type="button"
                variant="secondary"
                disabled={activeStep === 1 || saving}
                onClick={() => setActiveStep((current) => Math.max(1, current - 1))}
              >
                Voltar
              </Button>
              <div className="flex flex-col gap-3 sm:flex-row">
                {activeStep === 15 && canComplete && reviewMatchesSaved ? (
                  <Button type="button" busy={saving} onClick={() => void complete()}>
                    Concluir onboarding
                  </Button>
                ) : (
                  <Button type="submit" busy={saving} disabled={uploading || conflict}>
                    {saving ? "Salvando…" : activeStep === 15 ? "Salvar revisão final" : "Salvar e continuar"}
                  </Button>
                )}
              </div>
            </div>
          </form>

          {activeStep === 15 && onboarding.missing_steps.length > 0 ? (
            <div className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-bold">Ainda há etapas pendentes ou inválidas:</p>
              <p className="mt-1">{onboarding.missing_steps.map((step) => `${step}. ${ONBOARDING_STEPS[step - 1]}`).join("; ")}</p>
            </div>
          ) : null}
          {activeStep === 15 && dirtySteps.size > 0 ? (
            <div className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-bold">Há alterações locais ainda não salvas.</p>
              <p className="mt-1">
                Salve as etapas {Array.from(dirtySteps).sort((a, b) => a - b).join(", ")} antes de concluir.
              </p>
            </div>
          ) : null}
        </Card>
      </div>
    </>
  );
}
