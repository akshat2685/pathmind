import { Search, Bell } from "lucide-react";
import { Input } from "@/components/ui/input";

export function TopBar() {
  return (
    <header className="h-16 border-b border-border/50 glass flex items-center justify-between px-8 sticky top-0 z-10">
      <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
        <span className="hover:text-primary transition-colors cursor-pointer">Dashboard</span>
        <span className="text-border">/</span>
        <span className="text-foreground bg-clip-text">Overview</span>
      </div>
      
      <div className="flex items-center gap-6">
        <div className="relative w-64 hidden md:block">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input 
            type="search" 
            placeholder="Search resources, paths..." 
            className="w-full bg-muted/50 border-none pl-9 focus-visible:ring-1"
          />
        </div>
        <button className="relative text-muted-foreground hover:text-foreground transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-0 right-0 w-2 h-2 bg-primary rounded-full ring-2 ring-background"></span>
        </button>
      </div>
    </header>
  );
}
