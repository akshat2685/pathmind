import { cn } from "@/lib/utils";
import { LayoutDashboard, Compass, CheckSquare, BrainCircuit, Search, Bell, Settings, User } from "lucide-react";
import Link from "next/link";

export function Sidebar() {
  return (
    <aside className="w-64 flex flex-col border-r border-border/50 glass h-screen sticky top-0 z-20">
      <div className="h-16 flex items-center px-6 border-b border-border/50">
        <div className="font-sans font-bold tracking-wide text-lg flex items-center gap-2 group cursor-pointer">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg shadow-primary/20 group-hover:scale-105 transition-transform">
            <BrainCircuit className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">PATHMIND</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto py-6 px-4 flex flex-col gap-1">
        <div className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-widest mb-3 px-2">Navigation</div>
        <NavItem href="#" icon={<LayoutDashboard className="w-4 h-4" />} label="Dashboard" active />
        <NavItem href="#" icon={<Compass className="w-4 h-4" />} label="Trajectories" />
        <NavItem href="#" icon={<CheckSquare className="w-4 h-4" />} label="Evidence" />
        <NavItem href="#" icon={<BrainCircuit className="w-4 h-4" />} label="Memory" />
        
        <div className="mt-8 text-[10px] font-bold text-muted-foreground/70 uppercase tracking-widest mb-3 px-2">Settings</div>
        <NavItem href="#" icon={<Settings className="w-4 h-4" />} label="Preferences" />
      </div>
      
      <div className="p-4 m-4 rounded-xl glass-card flex items-center gap-3 hover:bg-muted/30 transition-colors cursor-pointer border border-border/50">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center border border-primary/20">
          <User className="w-4 h-4 text-primary" />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold">Student User</span>
          <span className="text-xs text-primary/80 font-medium">Level 2 Explorer</span>
        </div>
      </div>
    </aside>
  );
}

function NavItem({ href, icon, label, active }: { href: string; icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <Link 
      href={href}
      className={cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-300 relative overflow-hidden group",
        active 
          ? "text-primary font-medium shadow-sm" 
          : "text-muted-foreground hover:text-foreground"
      )}
    >
      {active && (
        <div className="absolute inset-0 bg-gradient-to-r from-primary/15 to-transparent opacity-100" />
      )}
      {!active && (
        <div className="absolute inset-0 bg-muted/50 opacity-0 group-hover:opacity-100 transition-opacity" />
      )}
      <div className="relative z-10 flex items-center gap-3">
        <div className={cn("transition-colors", active ? "text-primary" : "text-muted-foreground group-hover:text-primary/70")}>
          {icon}
        </div>
        {label}
      </div>
    </Link>
  );
}
