import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Queue } from "./pages/Queue";
import { Contests } from "./pages/Contests";
import { ContestDetail } from "./pages/ContestDetail";
import { Dashboard } from "./pages/Dashboard";
import { Teams } from "./pages/Teams";
import { Notes } from "./pages/Notes";
import { Settings } from "./pages/Settings";
import { Profile } from "./pages/Profile";
import { AILab } from "./pages/AILab";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ToastProvider } from "@/components/ui/toast";


function App() {
  return (
    <ToastProvider>
      <TooltipProvider>
        <Router>
        <div className="flex h-screen overflow-hidden bg-[#050505] text-foreground w-full">
          <Sidebar />
          <main className="flex-1 overflow-y-auto overflow-x-hidden">
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/" element={<Queue />} />
              <Route path="/contests" element={<Contests />} />
              <Route path="/contests/:id" element={<ContestDetail />} />
              <Route path="/ai-lab" element={<AILab />} />
              <Route path="/teams" element={<Teams />} />
              <Route path="/notes" element={<Notes />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/profile" element={<Profile />} />
            </Routes>
          </main>
        </div>
        </Router>
      </TooltipProvider>
    </ToastProvider>
  );
}

export default App;

