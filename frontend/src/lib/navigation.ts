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
      "CLIENT_OWNER",
      "CLIENT_REVIEWER",
    ],
  },
  { href: "/notificacoes", label: "Notificações", shortLabel: "Avisos" },
  {
    href: "/logs",
    label: "Registros",
    shortLabel: "Registros",
    roles: ["SUPER_ADMIN", "AGENCY_ADMIN"],
  },
  {
    href: "/equipe",
    label: "Equipe",
    shortLabel: "Equipe",
    roles: ["SUPER_ADMIN", "AGENCY_ADMIN", "CLIENT_OWNER"],
  },
];

export function navigationForRoles(roles: Role[]): NavigationItem[] {
  return NAVIGATION.filter(
    (item) => !item.roles || item.roles.some((role) => roles.includes(role)),
  );
}
