import { Progress } from "@/components/ui/progress";

export function ProgressIndicator({ value, label }: { value: number; label: string }) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground font-medium">{label}</span>
        <span className="text-foreground font-semibold">{value}%</span>
      </div>
      <Progress value={value} className="h-2 bg-muted" />
    </div>
  );
}
