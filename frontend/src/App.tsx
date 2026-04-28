import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Queue } from "./pages/Queue";
import { Contests } from "./pages/Contests";
import { ContestDetail } from "./pages/ContestDetail";

import { TooltipProvider } from "@/components/ui/tooltip";


function App() {
  return (
    <TooltipProvider>
      <Router>
      <div className="flex h-screen overflow-hidden bg-[#050505] text-foreground w-full">
        <Sidebar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <Routes>
            <Route path="/" element={<Queue />} />
            <Route path="/contests" element={<Contests />} />
            <Route path="/contests/:id" element={<ContestDetail />} />

          </Routes>
        </main>
      </div>
      </Router>
    </TooltipProvider>
  );
}

export default App;

