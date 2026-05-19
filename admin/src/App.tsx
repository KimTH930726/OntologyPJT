import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import DocumentDetail from "./pages/DocumentDetail";
import Candidates from "./pages/Candidates";
import Ontology from "./pages/Ontology";
import Graph from "./pages/Graph";
import QA from "./pages/QA";
import Audit from "./pages/Audit";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="documents" element={<Documents />} />
        <Route path="documents/:id" element={<DocumentDetail />} />
        <Route path="candidates" element={<Candidates />} />
        <Route path="ontology" element={<Ontology />} />
        <Route path="graph" element={<Graph />} />
        <Route path="qa" element={<QA />} />
        <Route path="audit" element={<Audit />} />
      </Route>
    </Routes>
  );
}
