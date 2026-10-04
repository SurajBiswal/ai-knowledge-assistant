import { useEffect, useState } from "react";
import llmProviderService from "../../services/llmProviderService";

const emptyForm = {
  profile_name: "",
  provider_id: "",
  base_url: "",
  model: "",
  timeout_seconds: "60",
  structured_json_responses: true,
  api_key: "",
};

function statusDetails(profile) {
  if (profile.last_test_status === "success") {
    return { label: "Connection verified", className: "text-moss" };
  }
  if (profile.last_test_status === "failed") {
    return { label: "Connection needs attention", className: "text-clay" };
  }
  return { label: "Not tested yet", className: "text-ink-400" };
}

function formatTestedAt(value) {
  if (!value) return null;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  return `Tested ${date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })}`;
}

function Notice({ type = "success", children }) {
  const styles = type === "error"
    ? "bg-clay-tint border-clay/30 text-clay-dark"
    : "bg-moss-tint border-moss/25 text-ink-900";

  return (
    <div className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${styles}`} role="status">
      <span className="mt-0.5 font-semibold" aria-hidden="true">
        {type === "error" ? "!" : "✓"}
      </span>
      <span>{children}</span>
    </div>
  );
}

function FieldLabel({ children, required = false }) {
  return (
    <span className="mb-1.5 block text-sm font-medium text-ink-900">
      {children}{required && <span className="ml-1 text-clay">*</span>}
    </span>
  );
}

function ProfileForm({ providers, profile, onCancel, onSaved }) {
  const isEditing = Boolean(profile);
  const [form, setForm] = useState(() => (
    profile
      ? {
        profile_name: profile.profile_name,
        provider_id: profile.provider_id,
        base_url: profile.base_url,
        model: profile.model,
        timeout_seconds: String(profile.timeout_seconds),
        structured_json_responses: profile.structured_json_responses,
        api_key: "",
      }
      : { ...emptyForm, provider_id: providers[0]?.id || "" }
  ));
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const update = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    const timeout = Number(form.timeout_seconds);
    if (!Number.isInteger(timeout) || timeout < 1) {
      setError("Timeout must be a whole number greater than zero.");
      return;
    }

    const payload = {
      profile_name: form.profile_name.trim(),
      provider_id: form.provider_id,
      base_url: form.base_url.trim(),
      model: form.model.trim(),
      timeout_seconds: timeout,
      structured_json_responses: form.structured_json_responses,
    };

    if (!isEditing || form.api_key.trim()) {
      payload.api_key = form.api_key.trim();
    }

    setIsSaving(true);
    try {
      const savedProfile = isEditing
        ? await llmProviderService.updateProfile(profile.id, payload)
        : await llmProviderService.createProfile(payload);
      onSaved(savedProfile, isEditing);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  };

  const inputClass = "w-full rounded-lg border border-paper-line bg-paper px-3 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 transition-colors focus:border-moss";

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div>
        <p className="font-display text-lg font-semibold text-ink-900">
          {isEditing ? "Edit provider profile" : "Add a language model"}
        </p>
        <p className="mt-1 text-sm leading-6 text-ink-600">
          {isEditing
            ? "Changing connection settings requires a new successful test before this profile can be active."
            : "Your API key is encrypted before it is stored and is never shown again."}
        </p>
      </div>

      {error && <Notice type="error">{error}</Notice>}

      <label className="block">
        <FieldLabel required>Profile name</FieldLabel>
        <input className={inputClass} value={form.profile_name} onChange={(event) => update("profile_name", event.target.value)} placeholder="Qwen production" required maxLength={100} />
      </label>

      <label className="block">
        <FieldLabel required>Provider protocol</FieldLabel>
        <select className={inputClass} value={form.provider_id} onChange={(event) => update("provider_id", event.target.value)} required>
          {providers.map((provider) => (
            <option key={provider.id} value={provider.id}>{provider.name}</option>
          ))}
        </select>
        <span className="mt-1.5 block text-xs text-ink-400">This protocol works with Qwen, DeepSeek, OpenAI, OpenRouter, vLLM, and other compatible endpoints.</span>
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block sm:col-span-2">
          <FieldLabel required>Base URL</FieldLabel>
          <input className={inputClass} value={form.base_url} onChange={(event) => update("base_url", event.target.value)} placeholder="https://api.example.com/v1" required maxLength={1000} autoComplete="url" />
        </label>
        <label className="block">
          <FieldLabel required>Model</FieldLabel>
          <input className={inputClass} value={form.model} onChange={(event) => update("model", event.target.value)} placeholder="qwen2.5-72b-instruct" required maxLength={255} />
        </label>
        <label className="block">
          <FieldLabel required>Timeout (seconds)</FieldLabel>
          <input className={inputClass} type="number" min="1" step="1" value={form.timeout_seconds} onChange={(event) => update("timeout_seconds", event.target.value)} required />
        </label>
      </div>

      <label className="block">
        <FieldLabel required={!isEditing}>API key</FieldLabel>
        <input className={inputClass} type="password" value={form.api_key} onChange={(event) => update("api_key", event.target.value)} placeholder={isEditing ? "Leave blank to keep the configured key" : "Paste your API key"} required={!isEditing} autoComplete="new-password" />
        {isEditing && profile.api_key_configured && <span className="mt-1.5 block text-xs text-ink-400">A credential is already configured. Leaving this blank keeps it unchanged.</span>}
      </label>

      <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-paper-line bg-paper-dim px-3 py-3">
        <input type="checkbox" checked={form.structured_json_responses} onChange={(event) => update("structured_json_responses", event.target.checked)} className="mt-0.5 h-4 w-4 accent-moss" />
        <span>
          <span className="block text-sm font-medium text-ink-900">Prefer structured JSON responses</span>
          <span className="mt-0.5 block text-xs leading-5 text-ink-600">Use JSON response formatting when the selected provider supports it.</span>
        </span>
      </label>

      <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
        <button type="button" onClick={onCancel} disabled={isSaving} className="rounded-lg border border-paper-line px-4 py-2.5 text-sm font-medium text-ink-600 hover:bg-paper-dim disabled:cursor-not-allowed disabled:opacity-60">Cancel</button>
        <button type="submit" disabled={isSaving || providers.length === 0} className="rounded-lg bg-moss px-4 py-2.5 text-sm font-semibold text-white hover:bg-moss-dark disabled:cursor-not-allowed disabled:opacity-60">
          {isSaving ? "Saving…" : isEditing ? "Save changes" : "Save profile"}
        </button>
      </div>
    </form>
  );
}

function ProfileCard({ profile, provider, pendingAction, onTest, onActivate, onEdit, onDelete }) {
  const status = statusDetails(profile);
  const testedAt = formatTestedAt(profile.last_tested_at);
  const isPending = Boolean(pendingAction);
  const canActivate = !profile.is_active && profile.last_test_status === "success";

  return (
    <article className={`rounded-xl border p-4 transition-colors ${profile.is_active ? "border-moss/40 bg-moss-tint/45" : "border-paper-line bg-surface"}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-base font-semibold text-ink-900">{profile.profile_name}</h3>
            {profile.is_active && <span className="rounded-full bg-moss px-2 py-0.5 text-[11px] font-semibold text-white">Active</span>}
          </div>
          <p className="mt-1 text-sm text-ink-600">{provider?.name || "Unknown provider"} · <span className="font-mono text-xs">{profile.model}</span></p>
          <p className="mt-1 truncate font-mono text-xs text-ink-400" title={profile.base_url}>{profile.base_url}</p>
        </div>
        <div className="text-left sm:text-right">
          <p className="text-xs text-ink-600">Credential: <span className={profile.api_key_configured ? "font-medium text-ink-900" : "text-clay"}>{profile.api_key_configured ? "Configured" : "Missing"}</span></p>
          <p className={`mt-1 text-xs font-medium ${status.className}`}>{status.label}</p>
          {testedAt && <p className="mt-1 text-[11px] text-ink-400">{testedAt}</p>}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-paper-line pt-3">
        <button type="button" onClick={() => onTest(profile)} disabled={isPending} className="rounded-md border border-paper-line px-3 py-2 text-sm font-medium text-ink-900 hover:bg-paper-dim disabled:cursor-not-allowed disabled:opacity-60">
          {pendingAction === "test" ? "Testing…" : "Test connection"}
        </button>
        {!profile.is_active && (
          <button type="button" onClick={() => onActivate(profile)} disabled={!canActivate || isPending} title={!canActivate ? "A successful connection test is required before activation." : undefined} className="rounded-md bg-moss px-3 py-2 text-sm font-semibold text-white hover:bg-moss-dark disabled:cursor-not-allowed disabled:opacity-45">
            {pendingAction === "activate" ? "Activating…" : "Activate"}
          </button>
        )}
        <button type="button" onClick={() => onEdit(profile)} disabled={isPending} className="rounded-md px-3 py-2 text-sm font-medium text-ink-600 hover:bg-paper-dim disabled:cursor-not-allowed disabled:opacity-60">Edit</button>
        {!profile.is_active && <button type="button" onClick={() => onDelete(profile)} disabled={isPending} className="rounded-md px-3 py-2 text-sm font-medium text-clay hover:bg-clay-tint disabled:cursor-not-allowed disabled:opacity-60">Delete</button>}
      </div>
      {!profile.is_active && !canActivate && <p className="mt-2 text-xs text-ink-400">Test this profile successfully before activating it.</p>}
    </article>
  );
}

export default function LanguageModelSettings({ onClose }) {
  const [providers, setProviders] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [notice, setNotice] = useState(null);
  const [formProfile, setFormProfile] = useState(undefined);
  const [pending, setPending] = useState(null);

  const refresh = async () => {
    setIsLoading(true);
    setLoadError("");
    try {
      const [availableProviders, savedProfiles] = await Promise.all([
        llmProviderService.listProviders(),
        llmProviderService.listProfiles(),
      ]);
      setProviders(availableProviders);
      setProfiles(savedProfiles);
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      llmProviderService.listProviders(),
      llmProviderService.listProfiles(),
    ])
      .then(([availableProviders, savedProfiles]) => {
        if (cancelled) return;
        setProviders(availableProviders);
        setProfiles(savedProfiles);
      })
      .catch((error) => {
        if (!cancelled) setLoadError(error.message);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  const setPendingAction = (profileId, action) => setPending({ profileId, action });
  const clearPending = () => setPending(null);

  const handleTest = async (profile) => {
    setNotice(null);
    setPendingAction(profile.id, "test");
    try {
      const result = await llmProviderService.testProfile(profile.id);
      setNotice({ type: result.success ? "success" : "error", message: result.message });
      await refresh();
    } catch (error) {
      setNotice({ type: "error", message: error.message });
    } finally {
      clearPending();
    }
  };

  const handleActivate = async (profile) => {
    setNotice(null);
    setPendingAction(profile.id, "activate");
    try {
      const result = await llmProviderService.activateProfile(profile.id);
      setNotice({ type: "success", message: result.message });
      await refresh();
    } catch (error) {
      setNotice({ type: "error", message: error.message });
    } finally {
      clearPending();
    }
  };

  const handleDelete = async (profile) => {
    if (!window.confirm(`Delete “${profile.profile_name}”? This cannot be undone.`)) return;

    setNotice(null);
    setPendingAction(profile.id, "delete");
    try {
      const result = await llmProviderService.deleteProfile(profile.id);
      setNotice({ type: "success", message: result.message });
      await refresh();
    } catch (error) {
      setNotice({ type: "error", message: error.message });
    } finally {
      clearPending();
    }
  };

  const handleSaved = async (savedProfile, wasEditing) => {
    setFormProfile(undefined);
    setNotice({
      type: "success",
      message: wasEditing
        ? "Profile updated. Test it again before activation if connection settings changed."
        : `“${savedProfile.profile_name}” was saved. Test the connection before activating it.`,
    });
    await refresh();
  };

  const providerById = new Map(providers.map((provider) => [provider.id, provider]));

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Language model settings">
      <button type="button" className="absolute inset-0 cursor-default bg-ink/55" onClick={onClose} aria-label="Close language model settings" />
      <section className="relative flex h-full w-full max-w-2xl flex-col bg-paper shadow-2xl">
        <header className="flex items-start justify-between border-b border-paper-line px-5 py-5 sm:px-7">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-moss">Settings</p>
            <h2 className="mt-1 font-display text-2xl font-semibold text-ink-900">Language model</h2>
            <p className="mt-1 text-sm text-ink-600">Choose the model the assistant uses for your conversations.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-md p-2 text-ink-600 hover:bg-paper-dim hover:text-ink-900" aria-label="Close settings">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" d="m6 6 12 12M18 6 6 18" /></svg>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-6 sm:px-7">
          {formProfile !== undefined ? (
            <ProfileForm providers={providers} profile={formProfile} onCancel={() => setFormProfile(undefined)} onSaved={handleSaved} />
          ) : (
            <div className="space-y-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="font-display text-lg font-semibold text-ink-900">Your provider profiles</h3>
                  <p className="mt-1 text-sm text-ink-600">You may save multiple profiles, but only one can be active.</p>
                </div>
                <button type="button" onClick={() => setFormProfile(null)} disabled={isLoading || providers.length === 0} className="inline-flex items-center justify-center gap-2 rounded-lg bg-moss px-4 py-2.5 text-sm font-semibold text-white hover:bg-moss-dark disabled:cursor-not-allowed disabled:opacity-60">
                  <span aria-hidden="true">+</span> Add provider
                </button>
              </div>

              {notice && <Notice type={notice.type}>{notice.message}</Notice>}
              {loadError && <Notice type="error">{loadError} <button type="button" onClick={refresh} className="ml-1 underline">Retry</button></Notice>}

              {isLoading ? (
                <div className="rounded-xl border border-paper-line bg-surface px-4 py-10 text-center text-sm text-ink-600">Loading provider profiles…</div>
              ) : profiles.length === 0 && !loadError ? (
                <div className="rounded-xl border border-dashed border-paper-line bg-surface px-5 py-10 text-center">
                  <p className="font-display text-lg font-semibold text-ink-900">No language model configured</p>
                  <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-600">Add an OpenAI-compatible provider profile to use your own Qwen, DeepSeek, OpenAI, OpenRouter, or local model endpoint.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {profiles.map((profile) => (
                    <ProfileCard key={profile.id} profile={profile} provider={providerById.get(profile.provider_id)} pendingAction={pending?.profileId === profile.id ? pending.action : null} onTest={handleTest} onActivate={handleActivate} onEdit={setFormProfile} onDelete={handleDelete} />
                  ))}
                </div>
              )}

              <p className="rounded-lg bg-paper-dim px-3 py-3 text-xs leading-5 text-ink-600">API keys are encrypted at rest and never returned to this browser. Changing an endpoint, model, key, or timeout requires a new successful connection test.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
