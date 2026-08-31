import { AppShell } from "@/components/layout/AppShell";
import { SectionHeader } from "@/components/pathmind/SectionHeader";
import { TrajectoryCard } from "@/components/pathmind/TrajectoryCard";
import { LockedStage } from "@/components/pathmind/LockedStage";
import { ProgressIndicator } from "@/components/pathmind/ProgressIndicator";
import { Button } from "@/components/ui/button";

export default function DesignSystemPage() {
  return (
    <AppShell>
      <div className="space-y-12 pb-24">
        
        {/* Header Section */}
        <section>
          <SectionHeader 
            title="Design System & Primitives" 
            description="A premium, intentional learning OS interface. Neutral foundations, strict hierarchy, and semantic state."
            action={<Button>Primary Action</Button>}
          />
        </section>

        {/* Typography & Colors */}
        <section className="space-y-4">
          <h3 className="text-lg font-medium text-muted-foreground uppercase tracking-widest text-xs">Surfaces & Typography</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="p-6 rounded-xl bg-card border border-border shadow-sm">
              <h4 className="text-2xl font-bold mb-2">Elevated Surface</h4>
              <p className="text-muted-foreground">Used for active cards, focus areas, and primary content. Notice the subtle border and lack of heavy drop shadows.</p>
            </div>
            <div className="p-6 rounded-xl bg-muted/50 border border-transparent">
              <h4 className="text-xl font-semibold mb-2 text-foreground/80">Muted Surface</h4>
              <p className="text-muted-foreground text-sm">Used for secondary information, backgrounds of locked states, and inactive regions.</p>
            </div>
          </div>
        </section>

        {/* Trajectory Cards */}
        <section className="space-y-4">
          <h3 className="text-lg font-medium text-muted-foreground uppercase tracking-widest text-xs">Candidate Paths</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <TrajectoryCard 
              title="Full-Stack Engineer"
              fitScore={92}
              description="Synthesized from your Python projects and interest in scalable systems. This path bridges your backend knowledge with modern React."
              requirements={["Advanced React", "System Design", "Cloud Deployments"]}
            />
            <TrajectoryCard 
              title="Data Engineer"
              fitScore={78}
              description="Leverages your strong algorithmic background, focusing on data pipelines and distributed storage."
              requirements={["SQL Optimization", "Apache Spark", "Airflow"]}
            />
          </div>
        </section>

        {/* Roadmap / Progress */}
        <section className="space-y-4">
          <h3 className="text-lg font-medium text-muted-foreground uppercase tracking-widest text-xs">Progressive Roadmap</h3>
          
          <div className="max-w-2xl bg-card p-6 rounded-xl border border-border/60 shadow-sm space-y-6 mb-8">
            <h4 className="font-semibold text-lg">Stage 1: Foundation (Active)</h4>
            <ProgressIndicator label="Stage Completion" value={65} />
            <p className="text-sm text-muted-foreground">You have submitted evidence for 2 of the 3 required milestones. The agent is waiting for your final architecture reflection.</p>
            <div className="flex gap-3 pt-2">
              <Button variant="default">Submit Evidence</Button>
              <Button variant="outline">View Memory Context</Button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl">
            <LockedStage 
              stage={2} 
              title="Advanced State Management" 
              description="Unlock this stage by demonstrating mastery of baseline React architecture and context isolation."
            />
            <LockedStage 
              stage={3} 
              title="Performance Optimization" 
              description="Requires completion of Stage 2. Focuses on rendering cycles and memorization."
            />
          </div>
        </section>

      </div>
    </AppShell>
  );
}
