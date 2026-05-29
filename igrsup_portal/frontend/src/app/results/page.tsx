import { AppShell } from "@/components/AppShell";
import { ResultsPanel } from "@/components/ResultsPanel";

export default function ResultsPage() {
  return (
    <AppShell>
      <section className="mb-6 rounded-[30px] border border-line bg-panel/35 px-6 py-5">
        <p className="text-xs uppercase tracking-[0.35em] text-accent">Results</p>
        <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-3xl font-semibold">Parcel score and intelligence briefing</h2>
            <p className="mt-2 max-w-3xl text-sm text-muted">
              Review the final ROCI score, inspect underlying components, understand legal and confidence risk, and evaluate nearby infrastructure signals from the same parcel response.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl">
        <ResultsPanel />
      </section>
    </AppShell>
  );
}
