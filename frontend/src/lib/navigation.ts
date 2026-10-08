import type { Role } from "@/types/api";

export interface NavigationItem {
  href: string;
  label: string;
  shortLabel: string;
  roles?: Role[];
}

export const NAVIGATION: NavigationItem[] = [
  { href: "/dashboard", label: "Início", shortLabel: "Início" },
  {
    href: "/clientes",
    label: "Clientes",
    shortLabel: "Clientes",
    roles: ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST"],
  },
  {
    href: "/comercial",
    label: "Pipeline comercial",
    shortLabel: "Comercial",
    roles: ["SUPER_ADMIN", "AGENCY_ADMIN", "STRATEGIST"],
  },
  {
    href: "/marca",
    label: "Marca e presets",
    shortLabel: "Marca",
  },
  {
    href: "/planejamento",
    label: "Planejamento",
    shortLabel: "Plano",
  },
  {
    href: "/midia",
    label: "Biblioteca de mídia",
    shortLabel: "Mídia",
  },
  {
    href: "/conteudos",
    label: "Conteúdos",
    shortLabel: "Conteúdo",
    roles: [
      "SUPER_ADMIN",
      "AGENCY_ADMIN",
      "STRATEGIST",
      "CONTENT_EDITOR",
      "DESIGNER",
      "CLIENT_OWNER",
      "CLIENT_REVIEWER",
      "VIEWER",
    ],
  },
  {
    href: "/aprovacoes",
    label: "Aprovações",
    shortLabel: "Aprovar",
    roles: [
      "SUPER_ADMIN",
      "AGENCY_ADMIN",
      "STRATEGIST",
      "CONTENT_EDITOR",
      "DESIGNER",
      "CLIENT_OWNER",
      "CLIENT_REVIEWER",
    ],
  },
  {
    href: "/relatorios",
    label: "Relatórios",
    shortLabel: "Dados",
  },
  { href: "/notificacoes", label: "Notificações", shortLabel: "Avisos" },
  {
    href: "/logs",
    label: "Registros",
    shortLabel: "Registros",
    roles: [
      "SUPER_ADMIN",
      "AGENCY_ADMIN",
      "STRATEGIST",
      "CONTENT_EDITOR",
      "DESIGNER",
      "CLIENT_OWNER",
      "CLIENT_REVIEWER",
    ],
  },
  {
    href: "/equipe",
    label: "Equipe",
    shortLabel: "Equipe",
    roles: ["SUPER_ADMIN", "AGENCY_ADMIN", "CLIENT_OWNER"],
  },
  {
    href: "/integracoes",
    label: "Integrações e providers",
    shortLabel: "Integrações",
    roles: ["SUPER_ADMIN", "AGENCY_ADMIN"],
  },
  { href: "/privacidade", label: "Privacidade e dados", shortLabel: "Privacidade" },
];

export function navigationForRoles(roles: Role[]): NavigationItem[] {
  return NAVIGATION.filter(
    (item) => !item.roles || item.roles.some((role) => roles.includes(role)),
  );
}
