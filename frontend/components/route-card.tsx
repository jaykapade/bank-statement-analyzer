import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

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
    <Link href={route.previewHref ?? route.href}>
      <Card className="rounded-[1.5rem] bg-white/4 transition hover:-translate-y-0.5 hover:bg-white/7">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-[var(--color-cyan)]">
                {route.href}
              </p>
              <h3 className="mt-2 font-mono text-xl font-semibold text-white">
                {route.title}
              </h3>
            </div>
            <Badge variant="secondary">{route.state}</Badge>
          </div>
          <p className="mt-3 text-sm leading-6 text-[var(--color-mist)]">
            {route.summary}
          </p>
          <p className="mt-4 text-xs uppercase tracking-[0.24em] text-white/45">
            Uses {route.endpoint}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
