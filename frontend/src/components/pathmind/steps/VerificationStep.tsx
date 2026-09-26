"use client";

import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { authedFetch } from "@/lib/api";

/**
 * A single verification field as described by the backend.
 *
 * Contract (backend: GET /api/orchestrate/verification/requirements):
 * {
 *   "user_type": "school",
 *   "title": "School Verification",
 *   "description": "Why we ask...",
 *   "fields": [ { "id", "label", "type", "required", "options?", "accept?", "hint?", "icon?" } ]
 * }
 * Field types: "text" | "number" | "select" | "textarea" | "file".
 */
export interface VerificationField {
  id: string;
  label: string;
  type: "text" | "number" | "select" | "textarea" | "file";
  required: boolean;
  options?: string[];
  accept?: string;
  hint?: string;
  icon?: string;
}

interface RequirementsResponse {
  user_type?: string;
  title?: string;
  description?: string;
  fields?: VerificationField[];
}

interface VerificationStepProps {
  userType: string;
  onNext: (data: Record<string, unknown>) => void;
  onBack: () => void;
}

type LoadStatus = "loading" | "ready" | "error";

const inputClass =
  "w-full hand-drawn-input text-base py-2 px-3 focus:outline-none";

function FileField({
  field,
  file,
  onSelect,
  error,
}: {
  field: VerificationField;
  file: File | null;
  onSelect: (f: File | null) => void;
  error?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files && e.target.files[0];
    onSelect(picked || null);
  };

  return (
    <div>
      <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
        {field.label}
        {field.required && <span className="text-error ml-1">*</span>}
      </label>
      <input
        type="file"
        ref={inputRef}
        className="hidden"
        accept={field.accept || "image/*,.pdf"}
        onChange={handleChange}
      />
      <div
        onClick={() => inputRef.current?.click()}
        className="w-full p-5 sketch-border bg-surface-container-low/80 hover:bg-surface-container-high/60 transition-all cursor-pointer flex items-center gap-4 border-dashed text-left"
      >
        <div className="w-11 h-11 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-2xl text-primary">
            {field.icon || "upload_file"}
          </span>
        </div>
        {file ? (
          <div className="flex-1 min-w-0">
            <p className="font-body-md text-sm text-on-surface truncate font-medium">
              {file.name}
            </p>
            <p className="font-note-handwritten text-base text-on-surface-variant">
              {(file.size / 1024).toFixed(1)} KB — tap to replace
            </p>
          </div>
        ) : (
          <div className="flex-1">
            <p className="font-body-md text-sm text-on-surface">
              Tap to attach {field.label.toLowerCase()}
            </p>
            <p className="font-note-handwritten text-base text-on-surface-variant">
              Photo or PDF — stored securely, never shared
            </p>
          </div>
        )}
        {file && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onSelect(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
            className="text-outline hover:text-error cursor-pointer shrink-0"
            aria-label="Remove file"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        )}
      </div>
      {field.hint && (
        <p className="text-[11px] text-on-surface-variant/80 mt-1 font-body-md">{field.hint}</p>
      )}
      {error && (
        <p className="text-xs text-error mt-1 font-body-md">{error}</p>
      )}
    </div>
  );
}

export function VerificationStep({ userType, onNext, onBack }: VerificationStepProps) {
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [loadError, setLoadError] = useState<string>("");
  const [title, setTitle] = useState<string>("Verify it's really you");
  const [description, setDescription] = useState<string>("");
  const [fields, setFields] = useState<VerificationField[]>([]);

  const [values, setValues] = useState<Record<string, string>>({});
  const [files, setFiles] = useState<Record<string, File>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setStatus("loading");
      setLoadError("");
      try {
        const res = await authedFetch(
          `/api/orchestrate/verification/requirements?user_type=${encodeURIComponent(userType)}`
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(
            body?.detail || `Verification service answered ${res.status}.`
          );
        }
        const data: RequirementsResponse = await res.json();
        if (cancelled) return;
        if (!data.fields || !Array.isArray(data.fields) || data.fields.length === 0) {
          throw new Error("Verification service returned no fields for this profile.");
        }
        setTitle(data.title || "Verify it's really you");
        setDescription(data.description || "");
        setFields(data.fields);
        setStatus("ready");
      } catch (err: unknown) {
        if (cancelled) return;
        const e = err as Error;
        setLoadError(
          e.message ||
            "Verification is unavailable right now. Your progress is saved — please try again."
        );
        setStatus("error");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [userType]);

  const setValue = (id: string, v: string) => {
    setValues((prev) => ({ ...prev, [id]: v }));
    setFieldErrors((prev) => {
      if (!prev[id]) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const setFile = (id: string, f: File | null) => {
    setFiles((prev) => {
      const next = { ...prev };
      if (f) next[id] = f;
      else delete next[id];
      return next;
    });
    setFieldErrors((prev) => {
      if (!prev[id]) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError("");

    // Client-side required check
    const errors: Record<string, string> = {};
    for (const f of fields) {
      if (!f.required) continue;
      if (f.type === "file") {
        if (!files[f.id]) errors[f.id] = `${f.label} is required.`;
      } else if (!(values[f.id] || "").trim()) {
        errors[f.id] = `${f.label} is required.`;
      }
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    // Build payload: file fields go as metadata only (no binary upload yet)
    const data: Record<string, unknown> = {};
    for (const f of fields) {
      if (f.type === "file") {
        const file = files[f.id];
        if (file) {
          data[f.id] = {
            file_name: file.name,
            file_size: file.size,
            file_type: file.type || "unknown",
          };
        }
      } else {
        data[f.id] = (values[f.id] || "").trim();
      }
    }

    setSubmitting(true);
    try {
      const res = await authedFetch("/api/orchestrate/verification/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_type: userType, data }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        // Backend may return per-field errors: { errors: { field_id: "msg" } }
        if (body && typeof body === "object" && body.errors && typeof body.errors === "object") {
          setFieldErrors(body.errors as Record<string, string>);
        }
        throw new Error(body?.detail || `Verification failed (${res.status}).`);
      }
      onNext(data);
    } catch (err: unknown) {
      const e = err as Error;
      setSubmitError(e.message || "Verification failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field: VerificationField) => {
    const error = fieldErrors[field.id];
    switch (field.type) {
      case "file":
        return (
          <FileField
            key={field.id}
            field={field}
            file={files[field.id] || null}
            onSelect={(f) => setFile(field.id, f)}
            error={error}
          />
        );
      case "select":
        return (
          <div key={field.id}>
            <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
              {field.label}
              {field.required && <span className="text-error ml-1">*</span>}
            </label>
            <select
              value={values[field.id] || ""}
              onChange={(ev) => setValue(field.id, ev.target.value)}
              className={`${inputClass} bg-surface-container-low cursor-pointer`}
            >
              <option value="">Select…</option>
              {(field.options || []).map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            {field.hint && (
              <p className="text-[11px] text-on-surface-variant/80 mt-1 font-body-md">{field.hint}</p>
            )}
            {error && <p className="text-xs text-error mt-1 font-body-md">{error}</p>}
          </div>
        );
      case "textarea":
        return (
          <div key={field.id}>
            <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
              {field.label}
              {field.required && <span className="text-error ml-1">*</span>}
            </label>
            <textarea
              value={values[field.id] || ""}
              onChange={(ev) => setValue(field.id, ev.target.value)}
              className={`${inputClass} h-24 resize-none`}
              placeholder={field.hint}
            />
            {error && <p className="text-xs text-error mt-1 font-body-md">{error}</p>}
          </div>
        );
      case "number":
        return (
          <div key={field.id}>
            <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
              {field.label}
              {field.required && <span className="text-error ml-1">*</span>}
            </label>
            <input
              type="number"
              value={values[field.id] || ""}
              onChange={(ev) => setValue(field.id, ev.target.value)}
              className={inputClass}
              placeholder={field.hint}
            />
            {error && <p className="text-xs text-error mt-1 font-body-md">{error}</p>}
          </div>
        );
      case "text":
      default:
        return (
          <div key={field.id}>
            <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
              {field.label}
              {field.required && <span className="text-error ml-1">*</span>}
            </label>
            <input
              type="text"
              value={values[field.id] || ""}
              onChange={(ev) => setValue(field.id, ev.target.value)}
              className={inputClass}
              placeholder={field.hint}
            />
            {error && <p className="text-xs text-error mt-1 font-body-md">{error}</p>}
          </div>
        );
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-3xl space-y-6"
    >
      <div className="text-center space-y-2">
        <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 inline-block">
          Chapter III: Proof of Identity
        </span>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface">
          Verify it&apos;s really you
        </h2>
        <p className="font-body-md text-on-surface-variant max-w-lg mx-auto">
          Personalization needs a real baseline. A quick check now means your
          path is built on who you actually are — not a guess.
        </p>
      </div>

      {status === "loading" && (
        <div className="sketch-border p-10 bg-surface-container-low/90 text-center flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center">
            <span className="material-symbols-outlined text-2xl text-primary animate-spin">
              auto_awesome
            </span>
          </div>
          <p className="font-note-handwritten text-xl text-secondary">
            Preparing your verification checklist…
          </p>
        </div>
      )}

      {status === "error" && (
        <div className="sketch-border p-6 bg-error/10 border-error/40 space-y-4">
          <div className="flex items-start gap-3">
            <span className="material-symbols-outlined text-2xl text-error shrink-0">
              error
            </span>
            <div>
              <p className="font-headline-sm text-lg text-on-surface mb-1">
                Verification isn&apos;t available yet
              </p>
              <p className="font-body-md text-sm text-on-surface-variant">
                {loadError}
              </p>
              <p className="font-body-md text-sm text-on-surface-variant mt-2">
                Nothing is lost — your aspiration and profile are saved. You can
                go back, or try loading this step again.
              </p>
            </div>
          </div>
          <div className="flex justify-between items-center pt-2 border-t border-error/20">
            <button
              type="button"
              onClick={onBack}
              className="ink-wash-btn px-6 py-2 text-lg cursor-pointer"
            >
              Back
            </button>
            <button
              type="button"
              onClick={() => {
                setStatus("loading");
                setLoadError("");
                // Re-trigger the effect by re-setting userType dependency indirectly:
                // simplest honest retry is a full reload of this step's data.
                window.location.reload();
              }}
              className="ink-wash-btn-primary px-6 py-2 text-lg cursor-pointer flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-base">refresh</span>
              <span>Try Again</span>
            </button>
          </div>
        </div>
      )}

      {status === "ready" && (
        <form onSubmit={handleSubmit} className="sketch-border p-6 sm:p-8 bg-surface-container-low/90 space-y-5">
          {(title !== "Verify it's really you" || description) && (
            <div className="flex items-center gap-2 text-secondary font-headline-sm text-sm pb-1 border-b border-outline/20">
              <span className="material-symbols-outlined text-base">verified</span>
              <span>{title}</span>
            </div>
          )}
          {description && (
            <p className="font-body-md text-sm text-on-surface-variant italic">{description}</p>
          )}

          {fields.map(renderField)}

          {submitError && (
            <div className="p-3 sketch-border bg-error/10 border-error/40 text-error text-sm font-body-md flex items-center gap-2">
              <span className="material-symbols-outlined text-lg shrink-0">error</span>
              <span>{submitError}</span>
            </div>
          )}

          <div className="flex justify-between items-center pt-4 border-t border-outline/20">
            <button
              type="button"
              onClick={onBack}
              className="ink-wash-btn px-6 py-2 text-lg cursor-pointer"
            >
              Back
            </button>
            <button
              type="submit"
              disabled={submitting}
              className={`px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer ${
                submitting
                  ? "opacity-50 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline"
                  : "ink-wash-btn-primary hover:-translate-y-0.5 transition-transform"
              }`}
            >
              <span>{submitting ? "Verifying…" : "Verify & Continue"}</span>
              <span className="material-symbols-outlined text-sm">east</span>
            </button>
          </div>
        </form>
      )}
    </motion.div>
  );
}
