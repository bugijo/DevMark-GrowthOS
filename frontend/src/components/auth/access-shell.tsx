import Link from "next/link";
import type { ReactNode } from "react";

export function AccessShell({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-8 sm:px-6">
      <div className="w-full max-w-lg">
        <Link
          href="/login"
          className="mb-6 inline-flex items-center gap-3 rounded-xl text-slate-950"
        >
          <span className="flex size-10 items-center justify-center rounded-xl bg-emerald-700 text-sm font-black text-white">
            GO
          </span>
          <span className="font-bold">DevMark GrowthOS</span>
        </Link>
        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
          <p className="text-xs font-bold tracking-widest text-emerald-700 uppercase">
            {eyebrow}
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            {title}
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>
          <div className="mt-7">{children}</div>
        </section>
      </div>
    </main>
  );
}
