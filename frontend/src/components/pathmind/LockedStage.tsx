import { Lock } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface LockedStageProps {
  stage: number;
  title: string;
  description: string;
}

export function LockedStage({ stage, title, description }: LockedStageProps) {
  return (
    <Card className="relative overflow-hidden border-border/30 bg-muted/20 opacity-70">
      <div className="absolute inset-0 bg-background/40 backdrop-blur-[2px] z-10 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-muted-foreground bg-background/80 px-4 py-2 rounded-full border border-border/50 shadow-sm">
          <Lock className="w-4 h-4" />
          <span className="text-xs font-medium uppercase tracking-widest">Locked</span>
        </div>
      </div>
      <CardHeader className="opacity-50">
        <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Stage {stage}</div>
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
    </Card>
  );
}
