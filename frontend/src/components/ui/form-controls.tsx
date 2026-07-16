"use client";

import {
  Children,
  cloneElement,
  type AriaAttributes,
  type ReactElement,
  useId,
} from "react";
import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

const controlClass =
  "mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-base text-slate-950 shadow-sm transition placeholder:text-slate-400 hover:border-slate-400 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100 aria-[invalid=true]:border-red-500 aria-[invalid=true]:focus:border-red-600 aria-[invalid=true]:focus:ring-red-100 sm:text-sm";

interface FieldControlProps {
  id?: string;
  required?: boolean;
  "aria-describedby"?: string;
  "aria-errormessage"?: string;
  "aria-invalid"?: AriaAttributes["aria-invalid"];
}

function mergeIds(...values: Array<string | undefined>): string | undefined {
  const ids = values
    .flatMap((value) => value?.split(/\s+/) ?? [])
    .filter(Boolean);
  const uniqueIds = Array.from(new Set(ids));
  return uniqueIds.length > 0 ? uniqueIds.join(" ") : undefined;
}

export function Field({
  id,
  label,
  hint,
  error,
  required,
  children,
}: {
  id?: string;
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactElement<FieldControlProps>;
}) {
  const generatedId = useId().replaceAll(":", "");
  const control = Children.only(children);
  const controlId = id ?? control.props.id ?? `field-${generatedId}`;
  const hintId = hint ? `${controlId}-hint` : undefined;
  const errorId = error ? `${controlId}-error` : undefined;
  const describedBy = mergeIds(
    control.props["aria-describedby"],
    hintId,
    errorId,
  );

  return (
    <div className="block">
      <label htmlFor={controlId} className="block text-sm font-semibold text-slate-800">
        {label}
        {required ? (
          <span className="ml-1 text-red-600" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {cloneElement(control, {
        id: controlId,
        required: required || control.props.required,
        "aria-describedby": describedBy,
        "aria-errormessage": errorId ?? control.props["aria-errormessage"],
        "aria-invalid": error ? true : control.props["aria-invalid"],
      })}
      {hint ? (
        <span
          id={hintId}
          className="mt-1.5 block text-xs font-normal text-slate-500"
        >
          {hint}
        </span>
      ) : null}
      {error ? (
        <span
          id={errorId}
          className="mt-1.5 block text-xs font-semibold text-red-700"
          role="alert"
        >
          {error}
        </span>
      ) : null}
    </div>
  );
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${controlClass} ${className}`} {...props} />;
}

export function Select({
  className = "",
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${controlClass} ${className}`} {...props} />;
}

export function Textarea({
  className = "",
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${controlClass} ${className}`} {...props} />;
}
