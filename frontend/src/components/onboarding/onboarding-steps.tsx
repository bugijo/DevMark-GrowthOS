"use client";

import type { ChangeEvent, Dispatch, SetStateAction } from "react";

import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/feedback";
import { Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import {
  NOTIFICATION_CATEGORIES,
  ONBOARDING_STEPS,
  type AudienceDraft,
  type ObjectiveDraft,
  type OnboardingFormState,
  type ServiceDraft,
  type StepValidationErrors,
} from "@/lib/onboarding";
import { ROLE_LABELS } from "@/lib/format";
import type {
  MediaAsset,
  NotificationCategory,
  OnboardingApprover,
  VisualPreset,
} from "@/types/api";

export interface OnboardingResources {
  media: MediaAsset[];
  approvers: OnboardingApprover[];
  presets: VisualPreset[];
  mediaError?: string;
  membersError?: string;
  presetsError?: string;
}

interface OnboardingStepFieldsProps {
  step: number;
  state: OnboardingFormState;
  setState: Dispatch<SetStateAction<OnboardingFormState | null>>;
  errors: StepValidationErrors;
  resources: OnboardingResources;
  uploading: boolean;
  allowUpload: boolean;
  uploadAsset: (file: File) => Promise<void>;
}

const listHint = "Use uma linha por item. Vírgulas também separam itens.";

function updateState(
  setState: Dispatch<SetStateAction<OnboardingFormState | null>>,
  update: (current: OnboardingFormState) => OnboardingFormState,
) {
  setState((current) => (current ? update(current) : current));
}

function toggleValue(values: string[], value: string, checked: boolean): string[] {
  return checked
    ? Array.from(new Set([...values, value]))
    : values.filter((item) => item !== value);
}

function SectionIntro({ step, children }: { step: number; children: string }) {
  return (
    <div className="mb-6">
      <p className="text-xs font-bold tracking-widest text-emerald-700 uppercase">
        Etapa {step} de {ONBOARDING_STEPS.length}
      </p>
      <h2
        id="onboarding-step-title"
        tabIndex={-1}
        className="mt-1 text-xl font-bold text-slate-950 sm:text-2xl"
      >
        {ONBOARDING_STEPS[step - 1]}
      </h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">{children}</p>
    </div>
  );
}

function ErrorSummary({ errors }: { errors: StepValidationErrors }) {
  const messages = Array.from(new Set(Object.values(errors)));
  return messages.length > 0 ? (
    <Alert>
      <p className="font-bold">Revise esta etapa:</p>
      <ul className="mt-1 list-disc pl-5">
        {messages.map((message) => (
          <li key={message}>{message}</li>
        ))}
      </ul>
    </Alert>
  ) : null;
}

function RepeaterHeader({
  title,
  onAdd,
}: {
  title: string;
  onAdd: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h3 className="font-bold text-slate-900">{title}</h3>
      <Button type="button" variant="secondary" onClick={onAdd}>
        Adicionar
      </Button>
    </div>
  );
}

function ServiceRows({
  items,
  setState,
}: {
  items: ServiceDraft[];
  setState: Dispatch<SetStateAction<OnboardingFormState | null>>;
}) {
  function update(index: number, field: keyof ServiceDraft, value: string) {
    updateState(setState, (current) => ({
      ...current,
      services: current.services.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    }));
  }

  return (
    <div className="space-y-4">
      <RepeaterHeader
        title={`Serviços (${items.length})`}
        onAdd={() =>
          updateState(setState, (current) => ({
            ...current,
            services: [
              ...current.services,
              { name: "", description: "", category: "", warnings: "" },
            ],
          }))
        }
      />
      {items.map((item, index) => (
        <fieldset key={item.id ?? index} className="rounded-xl border border-slate-200 p-4">
          <legend className="px-1 text-sm font-bold text-slate-700">
            Serviço {index + 1}
          </legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Nome" required>
              <Input value={item.name} onChange={(event) => update(index, "name", event.target.value)} />
            </Field>
            <Field label="Categoria">
              <Input value={item.category} onChange={(event) => update(index, "category", event.target.value)} />
            </Field>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="Descrição">
              <Textarea rows={3} value={item.description} onChange={(event) => update(index, "description", event.target.value)} />
            </Field>
            <Field label="Alertas e cuidados" hint={listHint}>
              <Textarea rows={3} value={item.warnings} onChange={(event) => update(index, "warnings", event.target.value)} />
            </Field>
          </div>
          {items.length > 1 ? (
            <Button
              type="button"
              variant="ghost"
              className="mt-3 text-red-700"
              onClick={() =>
                updateState(setState, (current) => ({
                  ...current,
                  services: current.services.filter((_, itemIndex) => itemIndex !== index),
                }))
              }
            >
              Remover serviço
            </Button>
          ) : null}
        </fieldset>
      ))}
    </div>
  );
}

function AudienceRows({
  items,
  setState,
}: {
  items: AudienceDraft[];
  setState: Dispatch<SetStateAction<OnboardingFormState | null>>;
}) {
  function update(index: number, field: keyof AudienceDraft, value: string) {
    updateState(setState, (current) => ({
      ...current,
      audiences: current.audiences.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    }));
  }

  return (
    <div className="space-y-4">
      <RepeaterHeader
        title={`Públicos (${items.length})`}
        onAdd={() =>
          updateState(setState, (current) => ({
            ...current,
            audiences: [
              ...current.audiences,
              { name: "", description: "", needs: "", objections: "", location: "" },
            ],
          }))
        }
      />
      {items.map((item, index) => (
        <fieldset key={item.id ?? index} className="rounded-xl border border-slate-200 p-4">
          <legend className="px-1 text-sm font-bold text-slate-700">Público {index + 1}</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Nome" required>
              <Input value={item.name} onChange={(event) => update(index, "name", event.target.value)} />
            </Field>
            <Field label="Localização">
              <Input value={item.location} onChange={(event) => update(index, "location", event.target.value)} />
            </Field>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <Field label="Descrição">
              <Textarea rows={3} value={item.description} onChange={(event) => update(index, "description", event.target.value)} />
            </Field>
            <Field label="Necessidades" hint={listHint}>
              <Textarea rows={3} value={item.needs} onChange={(event) => update(index, "needs", event.target.value)} />
            </Field>
            <Field label="Objeções" hint={listHint}>
              <Textarea rows={3} value={item.objections} onChange={(event) => update(index, "objections", event.target.value)} />
            </Field>
          </div>
          {items.length > 1 ? (
            <Button
              type="button"
              variant="ghost"
              className="mt-3 text-red-700"
              onClick={() =>
                updateState(setState, (current) => ({
                  ...current,
                  audiences: current.audiences.filter((_, itemIndex) => itemIndex !== index),
                }))
              }
            >
              Remover público
            </Button>
          ) : null}
        </fieldset>
      ))}
    </div>
  );
}

function ObjectiveRows({
  items,
  setState,
}: {
  items: ObjectiveDraft[];
  setState: Dispatch<SetStateAction<OnboardingFormState | null>>;
}) {
  function update(index: number, field: keyof ObjectiveDraft, value: string) {
    updateState(setState, (current) => ({
      ...current,
      objectives: current.objectives.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    }));
  }

  return (
    <div className="space-y-4">
      <RepeaterHeader
        title={`Objetivos (${items.length})`}
        onAdd={() =>
          updateState(setState, (current) => ({
            ...current,
            objectives: [...current.objectives, { name: "", description: "", indicators: "" }],
          }))
        }
      />
      {items.map((item, index) => (
        <fieldset key={item.id ?? index} className="rounded-xl border border-slate-200 p-4">
          <legend className="px-1 text-sm font-bold text-slate-700">Objetivo {index + 1}</legend>
          <Field label="Nome" required>
            <Input value={item.name} onChange={(event) => update(index, "name", event.target.value)} />
          </Field>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="Descrição">
              <Textarea rows={3} value={item.description} onChange={(event) => update(index, "description", event.target.value)} />
            </Field>
            <Field label="Indicadores planejados" hint={listHint}>
              <Textarea rows={3} value={item.indicators} onChange={(event) => update(index, "indicators", event.target.value)} />
            </Field>
          </div>
          {items.length > 1 ? (
            <Button
              type="button"
              variant="ghost"
              className="mt-3 text-red-700"
              onClick={() =>
                updateState(setState, (current) => ({
                  ...current,
                  objectives: current.objectives.filter((_, itemIndex) => itemIndex !== index),
                }))
              }
            >
              Remover objetivo
            </Button>
          ) : null}
        </fieldset>
      ))}
    </div>
  );
}

function MediaPicker({
  label,
  assets,
  selected,
  onChange,
  error,
  resourceError,
  uploading,
  allowUpload,
  uploadAsset,
}: {
  label: string;
  assets: MediaAsset[];
  selected: string[];
  onChange: (ids: string[]) => void;
  error?: string;
  resourceError?: string;
  uploading: boolean;
  allowUpload: boolean;
  uploadAsset: (file: File) => Promise<void>;
}) {
  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) await uploadAsset(file);
    event.target.value = "";
  }

  return (
    <div className="space-y-4">
      {resourceError ? <Alert>{resourceError}</Alert> : null}
      {allowUpload ? (
        <Field label={`Enviar novo ${label}`} hint="PNG, JPEG ou WebP. O backend valida tipo, tamanho e conteúdo.">
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            disabled={uploading}
            onChange={(event) => void chooseFile(event)}
            className="mt-1.5 block min-h-12 w-full rounded-xl border border-slate-300 bg-white p-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-3 file:py-2 file:font-semibold file:text-emerald-800"
          />
        </Field>
      ) : (
        <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
          Seu papel pode escolher imagens prontas, mas não enviar novos arquivos.
        </p>
      )}
      {uploading ? <p role="status" className="text-sm text-slate-600">Enviando e validando imagem…</p> : null}
      <fieldset>
        <legend className="text-sm font-semibold text-slate-800">Selecionar {label}</legend>
        {assets.length === 0 ? (
          <p className="mt-2 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
            Ainda não há imagens prontas. Envie uma imagem acima para continuar.
          </p>
        ) : (
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {assets.map((asset) => (
              <label key={asset.id} className="flex min-h-12 cursor-pointer items-start gap-3 rounded-xl border border-slate-200 p-3 text-sm hover:bg-slate-50">
                <input
                  type="checkbox"
                  checked={selected.includes(asset.id)}
                  onChange={(event) => onChange(toggleValue(selected, asset.id, event.target.checked))}
                  className="mt-0.5 size-5 accent-emerald-700"
                />
                <span>
                  <span className="block break-all font-semibold text-slate-900">{asset.display_name}</span>
                  <span className="text-xs text-slate-500">{asset.mime_type}</span>
                </span>
              </label>
            ))}
          </div>
        )}
      </fieldset>
      {error ? <p role="alert" className="text-sm font-semibold text-red-700">{error}</p> : null}
    </div>
  );
}

export function OnboardingStepFields({
  step,
  state,
  setState,
  errors,
  resources,
  uploading,
  allowUpload,
  uploadAsset,
}: OnboardingStepFieldsProps) {
  const imageAssets = resources.media.filter(
    (asset) => asset.mime_type.startsWith("image/") && asset.processing_status === "READY",
  );

  return (
    <div aria-labelledby="onboarding-step-title" className="space-y-5">
      <ErrorSummary errors={errors} />

      {step === 1 ? (
        <>
          <SectionIntro step={step}>Identifique a empresa e como a marca deve aparecer para o público.</SectionIntro>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Nome da empresa" required error={errors.name}>
              <Input value={state.company.name} onChange={(event) => updateState(setState, (current) => ({ ...current, company: { ...current.company, name: event.target.value } }))} />
            </Field>
            <Field label="Nome da marca" required error={errors.brandName}>
              <Input value={state.company.brandName} onChange={(event) => updateState(setState, (current) => ({ ...current, company: { ...current.company, brandName: event.target.value } }))} />
            </Field>
            <Field label="Nome público">
              <Input value={state.company.publicName} onChange={(event) => updateState(setState, (current) => ({ ...current, company: { ...current.company, publicName: event.target.value } }))} />
            </Field>
            <Field label="Fuso horário" required error={errors.timezone} hint="Ex.: America/Sao_Paulo">
              <Input value={state.company.timezone} onChange={(event) => updateState(setState, (current) => ({ ...current, company: { ...current.company, timezone: event.target.value } }))} />
            </Field>
          </div>
          <Field label="Descrição da empresa">
            <Textarea rows={4} value={state.company.description} onChange={(event) => updateState(setState, (current) => ({ ...current, company: { ...current.company, description: event.target.value } }))} />
          </Field>
        </>
      ) : null}

      {step === 2 ? (
        <>
          <SectionIntro step={step}>Informe o mercado principal. Isso ajuda a contextualizar estratégia e conteúdo.</SectionIntro>
          <Field label="Segmento" required error={errors.segment} hint="Ex.: clínica veterinária, contabilidade ou varejo local">
            <Input value={state.segment} onChange={(event) => updateState(setState, (current) => ({ ...current, segment: event.target.value }))} />
          </Field>
        </>
      ) : null}

      {step === 3 ? (
        <>
          <SectionIntro step={step}>Cadastre o que a empresa oferece. Cada item será salvo no catálogo real do cliente.</SectionIntro>
          <ServiceRows items={state.services} setState={setState} />
        </>
      ) : null}

      {step === 4 ? (
        <>
          <SectionIntro step={step}>Descreva as pessoas que a comunicação precisa alcançar.</SectionIntro>
          <AudienceRows items={state.audiences} setState={setState} />
        </>
      ) : null}

      {step === 5 ? (
        <>
          <SectionIntro step={step}>Registre resultados de marketing que possam ser acompanhados sem inventar métricas.</SectionIntro>
          <ObjectiveRows items={state.objectives} setState={setState} />
        </>
      ) : null}

      {step === 6 ? (
        <>
          <SectionIntro step={step}>Liste razões verdadeiras para o público escolher esta empresa.</SectionIntro>
          <Field label="Diferenciais" required error={errors.differentiators} hint={listHint}>
            <Textarea rows={6} value={state.differentiators} onChange={(event) => updateState(setState, (current) => ({ ...current, differentiators: event.target.value }))} />
          </Field>
        </>
      ) : null}

      {step === 7 ? (
        <>
          <SectionIntro step={step}>Defina como a marca fala e quais palavras combinam — ou não — com ela.</SectionIntro>
          <Field label="Descrição do tom de voz" required error={errors.tone}>
            <Textarea rows={4} value={state.tone.description} onChange={(event) => updateState(setState, (current) => ({ ...current, tone: { ...current.tone, description: event.target.value } }))} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Palavras preferidas" hint={listHint}>
              <Textarea rows={4} value={state.tone.preferredWords} onChange={(event) => updateState(setState, (current) => ({ ...current, tone: { ...current.tone, preferredWords: event.target.value } }))} />
            </Field>
            <Field label="Palavras que não devem ser usadas" hint={listHint}>
              <Textarea rows={4} value={state.tone.forbiddenWords} onChange={(event) => updateState(setState, (current) => ({ ...current, tone: { ...current.tone, forbiddenWords: event.target.value } }))} />
            </Field>
          </div>
        </>
      ) : null}

      {step === 8 ? (
        <>
          <SectionIntro step={step}>Escolha arquivos de logo já verificados ou envie um agora.</SectionIntro>
          <MediaPicker label="logo" assets={imageAssets} selected={state.logoIds} onChange={(ids) => updateState(setState, (current) => ({ ...current, logoIds: ids }))} error={errors.logos} resourceError={resources.mediaError} uploading={uploading} allowUpload={allowUpload} uploadAsset={uploadAsset} />
        </>
      ) : null}

      {step === 9 ? (
        <>
          <SectionIntro step={step}>Registre as escolhas visuais essenciais para manter consistência.</SectionIntro>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Cores principais" required error={errors.primaryColors} hint={listHint}>
              <Textarea rows={5} value={state.visual.primaryColors} onChange={(event) => updateState(setState, (current) => ({ ...current, visual: { ...current.visual, primaryColors: event.target.value } }))} placeholder="#146B5F" />
            </Field>
            <Field label="Cores secundárias" hint={listHint} error={errors.secondaryColors}>
              <Textarea rows={5} value={state.visual.secondaryColors} onChange={(event) => updateState(setState, (current) => ({ ...current, visual: { ...current.visual, secondaryColors: event.target.value } }))} />
            </Field>
            <Field label="Fontes" required error={errors.fonts} hint={listHint}>
              <Textarea rows={5} value={state.visual.fonts} onChange={(event) => updateState(setState, (current) => ({ ...current, visual: { ...current.visual, fonts: event.target.value } }))} placeholder="Inter" />
            </Field>
          </div>
        </>
      ) : null}

      {step === 10 ? (
        <>
          <SectionIntro step={step}>Selecione imagens que representem o estilo desejado. Não use dados pessoais ou clínicos.</SectionIntro>
          <MediaPicker label="referência visual" assets={imageAssets} selected={state.referenceIds} onChange={(ids) => updateState(setState, (current) => ({ ...current, referenceIds: ids }))} error={errors.references} resourceError={resources.mediaError} uploading={uploading} allowUpload={allowUpload} uploadAsset={uploadAsset} />
        </>
      ) : null}

      {step === 11 ? (
        <>
          <SectionIntro step={step}>Transforme o Brand Kit em orientações observáveis para texto e imagem.</SectionIntro>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="O que é permitido" required error={errors.allowed} hint={listHint}>
              <Textarea rows={5} value={state.rules.allowed} onChange={(event) => updateState(setState, (current) => ({ ...current, rules: { ...current.rules, allowed: event.target.value } }))} />
            </Field>
            <Field label="O que é proibido" required error={errors.forbidden} hint={listHint}>
              <Textarea rows={5} value={state.rules.forbidden} onChange={(event) => updateState(setState, (current) => ({ ...current, rules: { ...current.rules, forbidden: event.target.value } }))} />
            </Field>
            <Field label="Termos obrigatórios" hint={listHint}>
              <Textarea rows={4} value={state.rules.requiredTerms} onChange={(event) => updateState(setState, (current) => ({ ...current, rules: { ...current.rules, requiredTerms: event.target.value } }))} />
            </Field>
            <Field label="Regras legais ou profissionais" hint={listHint}>
              <Textarea rows={4} value={state.rules.legal} onChange={(event) => updateState(setState, (current) => ({ ...current, rules: { ...current.rules, legal: event.target.value } }))} />
            </Field>
          </div>
          <Field label="Restrições para imagens" hint={listHint}>
            <Textarea rows={4} value={state.rules.imageRestrictions} onChange={(event) => updateState(setState, (current) => ({ ...current, rules: { ...current.rules, imageRestrictions: event.target.value } }))} />
          </Field>
        </>
      ) : null}

      {step === 12 ? (
        <>
          <SectionIntro step={step}>Defina quem, na empresa cliente, pode decidir aprovações.</SectionIntro>
          {resources.membersError ? <Alert>{resources.membersError}</Alert> : null}
          <fieldset>
            <legend className="text-sm font-semibold text-slate-800">Responsáveis</legend>
            {resources.approvers.length === 0 ? (
              <p className="mt-2 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
                Nenhum aprovador ativo foi encontrado. Convide um proprietário ou revisor do cliente na página Equipe.
              </p>
            ) : (
              <div className="mt-2 space-y-2">
                {resources.approvers.map((approver) => (
                  <label key={approver.membership_id} className="flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border border-slate-200 p-3 hover:bg-slate-50">
                    <input
                      type="checkbox"
                      checked={state.approverIds.includes(approver.membership_id)}
                      onChange={(event) => updateState(setState, (current) => ({ ...current, approverIds: toggleValue(current.approverIds, approver.membership_id, event.target.checked) }))}
                      className="size-5 accent-emerald-700"
                    />
                    <span className="min-w-0 text-sm">
                      <span className="block truncate font-semibold text-slate-900">{approver.name || approver.email}</span>
                      <span className="block truncate text-xs text-slate-500">{ROLE_LABELS[approver.role]} · {approver.email}</span>
                    </span>
                  </label>
                ))}
              </div>
            )}
          </fieldset>
          {errors.approvers ? <p role="alert" className="text-sm font-semibold text-red-700">{errors.approvers}</p> : null}
        </>
      ) : null}

      {step === 13 ? (
        <>
          <SectionIntro step={step}>Escolha uma configuração inicial. Cada pessoa poderá ajustar suas preferências depois.</SectionIntro>
          <label className="flex min-h-12 items-center gap-3 rounded-xl border border-slate-200 p-3 text-sm font-semibold text-slate-800">
            <input type="checkbox" checked={state.notifications.emailEnabled} onChange={(event) => updateState(setState, (current) => ({ ...current, notifications: { ...current.notifications, emailEnabled: event.target.checked } }))} className="size-5 accent-emerald-700" />
            Receber notificações por e-mail
          </label>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Frequência" required>
              <Select value={state.notifications.mode} onChange={(event) => updateState(setState, (current) => ({ ...current, notifications: { ...current.notifications, mode: event.target.value as OnboardingFormState["notifications"]["mode"] } }))}>
                <option value="IMMEDIATE">Imediata</option>
                <option value="DAILY">Resumo diário</option>
                <option value="WEEKLY">Resumo semanal</option>
                <option value="URGENT_ONLY">Somente urgente</option>
              </Select>
            </Field>
            <Field label="Fuso horário" required error={errors.notificationTimezone}>
              <Input value={state.notifications.timezone} onChange={(event) => updateState(setState, (current) => ({ ...current, notifications: { ...current.notifications, timezone: event.target.value } }))} />
            </Field>
            <Field label="Horário do resumo" required error={errors.digestTime}>
              <Input type="time" value={state.notifications.digestTime} onChange={(event) => updateState(setState, (current) => ({ ...current, notifications: { ...current.notifications, digestTime: event.target.value } }))} />
            </Field>
          </div>
          {state.notifications.mode === "WEEKLY" ? (
            <Field label="Dia do resumo semanal" required>
              <Select value={state.notifications.weeklyDay} onChange={(event) => updateState(setState, (current) => ({ ...current, notifications: { ...current.notifications, weeklyDay: Number(event.target.value) } }))}>
                <option value={0}>Segunda-feira</option>
                <option value={1}>Terça-feira</option>
                <option value={2}>Quarta-feira</option>
                <option value={3}>Quinta-feira</option>
                <option value={4}>Sexta-feira</option>
                <option value={5}>Sábado</option>
                <option value={6}>Domingo</option>
              </Select>
            </Field>
          ) : null}
          <fieldset>
            <legend className="text-sm font-semibold text-slate-800">Não enviar estas categorias</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {NOTIFICATION_CATEGORIES.map((category) => (
                <label key={category.value} className="flex min-h-11 items-center gap-3 rounded-xl border border-slate-200 p-3 text-sm">
                  <input
                    type="checkbox"
                    checked={state.notifications.disabledCategories.includes(category.value)}
                    onChange={(event) =>
                      updateState(setState, (current) => ({
                        ...current,
                        notifications: {
                          ...current.notifications,
                          disabledCategories: toggleValue(
                            current.notifications.disabledCategories,
                            category.value,
                            event.target.checked,
                          ) as NotificationCategory[],
                        },
                      }))
                    }
                    className="size-5 accent-emerald-700"
                  />
                  {category.label}
                </label>
              ))}
            </div>
          </fieldset>
        </>
      ) : null}

      {step === 14 ? (
        <>
          <SectionIntro step={step}>Vincule um preset pronto ou crie uma base segura usando as escolhas do Brand Kit.</SectionIntro>
          {resources.presetsError ? <Alert>{resources.presetsError}</Alert> : null}
          <fieldset className="space-y-2">
            <legend className="text-sm font-semibold text-slate-800">Origem do preset</legend>
            <label className="flex min-h-11 items-center gap-3 rounded-xl border border-slate-200 p-3 text-sm">
              <input type="radio" name="preset-source" value="existing" checked={state.preset.source === "existing"} onChange={() => updateState(setState, (current) => ({ ...current, preset: { ...current.preset, source: "existing" } }))} className="size-5 accent-emerald-700" />
              Usar um preset existente
            </label>
            <label className="flex min-h-11 items-center gap-3 rounded-xl border border-slate-200 p-3 text-sm">
              <input type="radio" name="preset-source" value="new" checked={state.preset.source === "new"} onChange={() => updateState(setState, (current) => ({ ...current, preset: { ...current.preset, source: "new" } }))} className="size-5 accent-emerald-700" />
              Criar um preset inicial
            </label>
          </fieldset>
          {state.preset.source === "existing" ? (
            <Field label="Preset visual" required error={errors.preset}>
              <Select value={state.preset.presetId} onChange={(event) => updateState(setState, (current) => ({ ...current, preset: { ...current.preset, presetId: event.target.value } }))}>
                <option value="">Selecione…</option>
                {resources.presets.map((preset) => (
                  <option key={preset.id} value={preset.id}>{preset.name} · {preset.format} · {preset.aspect_ratio}</option>
                ))}
              </Select>
            </Field>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Nome do preset" required error={errors.presetName}>
                <Input value={state.preset.name} onChange={(event) => updateState(setState, (current) => ({ ...current, preset: { ...current.preset, name: event.target.value } }))} />
              </Field>
              <Field label="Objetivo visual">
                <Input value={state.preset.objective} onChange={(event) => updateState(setState, (current) => ({ ...current, preset: { ...current.preset, objective: event.target.value } }))} />
              </Field>
              <Field label="Formato" required error={errors.presetFormat}>
                <Input value={state.preset.format} onChange={(event) => updateState(setState, (current) => ({ ...current, preset: { ...current.preset, format: event.target.value } }))} placeholder="FEED" />
              </Field>
              <Field label="Proporção" required error={errors.presetAspect}>
                <Input value={state.preset.aspectRatio} onChange={(event) => updateState(setState, (current) => ({ ...current, preset: { ...current.preset, aspectRatio: event.target.value } }))} placeholder="1:1" />
              </Field>
              <Field label="Modo de criação" required>
                <Select value={state.preset.creationMode} onChange={(event) => updateState(setState, (current) => ({ ...current, preset: { ...current.preset, creationMode: event.target.value as OnboardingFormState["preset"]["creationMode"] } }))}>
                  <option value="TEMPLATE">Template</option>
                  <option value="MANUAL">Manual</option>
                  <option value="HYBRID">Híbrido com provider mock</option>
                  <option value="AI_IMAGE">Imagem com provider mock</option>
                </Select>
              </Field>
            </div>
          )}
        </>
      ) : null}

      {step === 15 ? (
        <>
          <SectionIntro step={step}>Confira os principais vínculos. Você ainda pode voltar e corrigir qualquer etapa.</SectionIntro>
          <dl className="grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
            <div><dt className="text-slate-500">Empresa</dt><dd className="font-bold text-slate-900">{state.company.name}</dd></div>
            <div><dt className="text-slate-500">Segmento</dt><dd className="font-bold text-slate-900">{state.segment}</dd></div>
            <div><dt className="text-slate-500">Serviços</dt><dd className="font-bold text-slate-900">{state.services.length}</dd></div>
            <div><dt className="text-slate-500">Públicos</dt><dd className="font-bold text-slate-900">{state.audiences.length}</dd></div>
            <div><dt className="text-slate-500">Objetivos</dt><dd className="font-bold text-slate-900">{state.objectives.length}</dd></div>
            <div><dt className="text-slate-500">Aprovadores</dt><dd className="font-bold text-slate-900">{state.approverIds.length}</dd></div>
            <div><dt className="text-slate-500">Logos</dt><dd className="font-bold text-slate-900">{state.logoIds.length}</dd></div>
            <div><dt className="text-slate-500">Referências visuais</dt><dd className="font-bold text-slate-900">{state.referenceIds.length}</dd></div>
          </dl>
          <Field label="Observações finais">
            <Textarea rows={4} value={state.review.notes} onChange={(event) => updateState(setState, (current) => ({ ...current, review: { ...current.review, notes: event.target.value } }))} />
          </Field>
          <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-4 text-sm font-semibold text-slate-800">
            <input type="checkbox" checked={state.review.confirmed} onChange={(event) => updateState(setState, (current) => ({ ...current, review: { ...current.review, confirmed: event.target.checked } }))} className="mt-0.5 size-5 accent-emerald-700" />
            Revisei os dados e confirmo que não incluí informações clínicas, segredos ou dados pessoais desnecessários.
          </label>
          {errors.confirmed ? <p role="alert" className="text-sm font-semibold text-red-700">{errors.confirmed}</p> : null}
        </>
      ) : null}
    </div>
  );
}
