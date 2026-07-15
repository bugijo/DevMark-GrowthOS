import type { ContentStatus, Role, User } from "@/types/api";

export const STATUS_LABELS: Record<ContentStatus, string> = {
  DRAFT: "Rascunho",
  INTERNAL_REVIEW: "Revisão interna",
  CLIENT_REVIEW: "Aguardando cliente",
  CHANGES_REQUESTED: "Alterações pedidas",
  APPROVED: "Aprovado",
  SCHEDULED: "Agendado",
  PUBLISHED: "Publicado",
  FAILED: "Falhou",
  ARCHIVED: "Arquivado",
};

export const ROLE_LABELS: Record<Role, string> = {
  SUPER_ADMIN: "Administração da plataforma",
  AGENCY_ADMIN: "Administração da agência",
  STRATEGIST: "Estratégia",
  CONTENT_EDITOR: "Edição de conteúdo",
  DESIGNER: "Design",
  CLIENT_OWNER: "Responsável do cliente",
  CLIENT_REVIEWER: "Revisão do cliente",
  VIEWER: "Somente leitura",
};

export function displayName(user: User): string {
  return user.name ?? user.full_name ?? user.email.split("@")[0];
}

export function formatDateTime(value?: string): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export function splitCommaSeparated(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinCommaSeparated(value?: string[]): string {
  return value?.join(", ") ?? "";
}
