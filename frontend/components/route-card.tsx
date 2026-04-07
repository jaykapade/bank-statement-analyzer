import Link from "next/link";

type Route = {
  href: string;
  previewHref?: string;
  title: string;
  summary: string;
  endpoint: string;
  state: string;
};

export function RouteCard({ route }: { route: Route }) {
  return (
    <Link
      href={route.previewHref ?? route.href}
      className="group rounded-[1.5rem] border border-white/10 bg-white/4 p-5 transition hover:-translate-y-0.5 hover:border-[var(--color-sand)]/40 hover:bg-white/7"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--color-sand)]">
            {route.href}
          </p>
          <h3 className="mt-2 font-mono text-xl font-semibold text-white">
            {route.title}
          </h3>
        </div>
        <span className="pill">{route.state}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--color-mist)]">{route.summary}</p>
      <p className="mt-4 text-xs uppercase tracking-[0.24em] text-white/45">
        Uses {route.endpoint}
      </p>
    </Link>
  );
}
