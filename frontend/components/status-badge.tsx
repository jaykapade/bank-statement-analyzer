import { Badge } from "@/components/ui/badge";

const statusStyles: Record<string, string> = {
  completed: "success",
  categorizing: "warning",
  extracting: "info",
  extracted: "accent",
  pending: "default",
  failed: "destructive",
  extract_failed: "destructive",
  categorize_failed: "destructive",
  "needs-attention": "destructive",
  stable: "success",
  active: "warning",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={statusStyles[status] as never}>
      {status}
    </Badge>
  );
}
