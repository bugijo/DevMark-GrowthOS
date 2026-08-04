import Link from "next/link";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Breadcrumbs({
  items,
  className = "",
}: {
  items: BreadcrumbItem[];
  className?: string;
}) {
  if (items.length === 0) return null;

  return (
    <nav
      aria-label="Navegação estrutural"
      className={`text-sm text-slate-600 ${className}`}
    >
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {items.map((item, index) => {
          const current = index === items.length - 1;
          return (
            <li key={`${item.label}-${index}`} className="flex min-w-0 items-center gap-2">
              {index > 0 ? (
                <span aria-hidden="true" className="text-slate-400">
                  /
                </span>
              ) : null}
              {current ? (
                <span aria-current="page" className="truncate font-semibold text-slate-800">
                  {item.label}
                </span>
              ) : item.href ? (
                <Link
                  href={item.href}
                  className="rounded font-semibold text-emerald-700 underline decoration-emerald-300 underline-offset-4 hover:text-emerald-900"
                >
                  {item.label}
                </Link>
              ) : (
                <span>{item.label}</span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
