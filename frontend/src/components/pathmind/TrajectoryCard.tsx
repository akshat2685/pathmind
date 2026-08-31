import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, GitMerge, TrendingUp } from "lucide-react";

interface TrajectoryCardProps {
  title: string;
  fitScore: number;
  description: string;
  requirements: string[];
}

export function TrajectoryCard({ title, fitScore, description, requirements }: TrajectoryCardProps) {
  return (
    <Card className="flex flex-col h-full glass-card hover:-translate-y-1 hover:shadow-xl hover:shadow-primary/5 hover:border-primary/30 transition-all duration-300 relative overflow-hidden group">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      <CardHeader>
        <div className="flex items-start justify-between mb-2">
          <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
            <TrendingUp className="w-3 h-3 mr-1" />
            {fitScore}% Fit
          </Badge>
          <GitMerge className="w-4 h-4 text-muted-foreground" />
        </div>
        <CardTitle className="text-xl">{title}</CardTitle>
        <CardDescription className="line-clamp-2">{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="text-sm font-medium text-muted-foreground mb-2">Key Requirements:</div>
        <ul className="flex flex-wrap gap-2">
          {requirements.map((req, i) => (
            <li key={i} className="text-xs bg-muted px-2 py-1 rounded-md text-foreground/80 border border-border/50">
              {req}
            </li>
          ))}
        </ul>
      </CardContent>
      <CardFooter>
        <button className="text-sm font-medium text-primary flex items-center gap-2 hover:gap-3 transition-all">
          Explore this path <ArrowRight className="w-4 h-4" />
        </button>
      </CardFooter>
    </Card>
  );
}
