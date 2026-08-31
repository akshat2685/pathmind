"use client";

import { motion } from "framer-motion";
import { useState, useRef } from "react";

export interface EvidenceItem {
  source: string;
  type: string; // file, link, project_description
  name: string;
  description: string;
  url?: string;
  confidence: string;
  timestamp: string;
}

interface EvidenceStepProps {
  onNext: (evidenceList: EvidenceItem[]) => void;
  onBack: () => void;
}

export function EvidenceStep({ onNext, onBack }: EvidenceStepProps) {
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [activeTab, setActiveTab] = useState<"files" | "links" | "projects">("files");
  
  // Link form state
  const [linkUrl, setLinkUrl] = useState("");
  const [linkLabel, setLinkLabel] = useState("");

  // Project form state
  const [projectTitle, setProjectTitle] = useState("");
  const [projectDesc, setProjectDesc] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle Real File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    const files = Array.from(e.target.files);
    const newItems: EvidenceItem[] = files.map((file) => ({
      source: "candidate_upload",
      type: "file",
      name: file.name,
      description: `Uploaded file (${(file.size / 1024).toFixed(1)} KB, type: ${file.type || "document"})`,
      confidence: "HIGH",
      timestamp: new Date().toISOString()
    }));

    const updated = [...evidenceList, ...newItems];
    setEvidenceList(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("pathmind_user_evidence", JSON.stringify(updated));
    }
  };

  // Add Link
  const handleAddLink = (e: React.FormEvent) => {
    e.preventDefault();
    if (!linkUrl.trim()) return;

    const newItem: EvidenceItem = {
      source: "candidate_portfolio_link",
      type: "link",
      name: linkLabel.trim() || linkUrl.trim(),
      description: `Portfolio URL / Code Repository: ${linkUrl.trim()}`,
      url: linkUrl.trim(),
      confidence: "HIGH",
      timestamp: new Date().toISOString()
    };

    const updated = [...evidenceList, newItem];
    setEvidenceList(updated);
    setLinkUrl("");
    setLinkLabel("");
    if (typeof window !== "undefined") {
      localStorage.setItem("pathmind_user_evidence", JSON.stringify(updated));
    }
  };

  // Add Project
  const handleAddProject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectTitle.trim()) return;

    const newItem: EvidenceItem = {
      source: "candidate_project_record",
      type: "project_description",
      name: projectTitle.trim(),
      description: projectDesc.trim() || `Verified project artifact: ${projectTitle.trim()}`,
      confidence: "HIGH",
      timestamp: new Date().toISOString()
    };

    const updated = [...evidenceList, newItem];
    setEvidenceList(updated);
    setProjectTitle("");
    setProjectDesc("");
    if (typeof window !== "undefined") {
      localStorage.setItem("pathmind_user_evidence", JSON.stringify(updated));
    }
  };

  // Remove Item
  const handleRemoveItem = (index: number) => {
    const updated = evidenceList.filter((_, i) => i !== index);
    setEvidenceList(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("pathmind_user_evidence", JSON.stringify(updated));
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="max-w-3xl mx-auto px-4 py-8"
    >
      <div className="mb-8 text-center">
        <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 mb-2 inline-block">
          Evidence Scribing
        </span>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">
          Upload Portfolio &amp; Evidence
        </h2>
        <p className="font-body-md text-on-surface-variant max-w-lg mx-auto">
          Upload project files, GitHub repositories, or transcripts. The zero-assumption counseling agent requires concrete evidence to substantiate your career trajectory.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex justify-center gap-3 mb-6">
        <button
          type="button"
          onClick={() => setActiveTab("files")}
          className={`px-4 py-1.5 font-headline-sm text-base transition-all cursor-pointer ${
            activeTab === "files" ? "ink-wash-btn-primary" : "ink-wash-btn text-on-surface-variant"
          }`}
        >
          <span className="material-symbols-outlined text-sm mr-1.5">upload_file</span>
          Upload Files
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("links")}
          className={`px-4 py-1.5 font-headline-sm text-base transition-all cursor-pointer ${
            activeTab === "links" ? "ink-wash-btn-primary" : "ink-wash-btn text-on-surface-variant"
          }`}
        >
          <span className="material-symbols-outlined text-sm mr-1.5">link</span>
          Portfolio / GitHub Links
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("projects")}
          className={`px-4 py-1.5 font-headline-sm text-base transition-all cursor-pointer ${
            activeTab === "projects" ? "ink-wash-btn-primary" : "ink-wash-btn text-on-surface-variant"
          }`}
        >
          <span className="material-symbols-outlined text-sm mr-1.5">code_blocks</span>
          Project Artifacts
        </button>
      </div>

      {/* Tab 1: Real File Upload */}
      {activeTab === "files" && (
        <div className="mb-8">
          <input
            type="file"
            multiple
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.doc,.docx,.txt,.md,.json,.zip,.py,.js,.ts,.tsx"
            className="hidden"
          />
          <div
            onClick={() => fileInputRef.current?.click()}
            className="w-full p-8 sketch-border bg-surface-container-low/80 hover:bg-surface-container-high/60 transition-all cursor-pointer flex flex-col items-center justify-center border-dashed text-center group"
          >
            <div className="w-14 h-14 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
              <span className="material-symbols-outlined text-3xl text-primary">
                cloud_upload
              </span>
            </div>
            <p className="font-headline-sm text-xl text-on-surface mb-1">
              Click to select files from your computer
            </p>
            <p className="font-note-handwritten text-lg text-on-surface-variant">
              PDF Resumes, transcripts, project documentation, markdown, or code packages
            </p>
          </div>
        </div>
      )}

      {/* Tab 2: Link Input */}
      {activeTab === "links" && (
        <form onSubmit={handleAddLink} className="mb-8 p-6 sketch-border bg-surface-container-low/90 space-y-4">
          <div>
            <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
              Portfolio / GitHub / Project Link
            </label>
            <input
              type="url"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              placeholder="https://github.com/username/project or portfolio link"
              className="w-full hand-drawn-input px-2 py-1 text-lg"
            />
          </div>
          <div>
            <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
              Label / Description (Optional)
            </label>
            <input
              type="text"
              value={linkLabel}
              onChange={(e) => setLinkLabel(e.target.value)}
              placeholder="e.g. Distributed Cloud Systems GitHub Repo"
              className="w-full hand-drawn-input px-2 py-1 text-lg"
            />
          </div>
          <div className="flex justify-end pt-2">
            <button type="submit" className="ink-wash-btn-primary px-6 py-1.5 text-lg flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">add</span>
              <span>Add Link</span>
            </button>
          </div>
        </form>
      )}

      {/* Tab 3: Project Builder */}
      {activeTab === "projects" && (
        <form onSubmit={handleAddProject} className="mb-8 p-6 sketch-border bg-surface-container-low/90 space-y-4">
          <div>
            <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
              Project Title &amp; Domain
            </label>
            <input
              type="text"
              value={projectTitle}
              onChange={(e) => setProjectTitle(e.target.value)}
              placeholder="e.g., High-Throughput Distributed Cache in Rust"
              className="w-full hand-drawn-input px-2 py-1 text-lg"
            />
          </div>
          <div>
            <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
              Key Contributions &amp; Applied Technologies
            </label>
            <textarea
              value={projectDesc}
              onChange={(e) => setProjectDesc(e.target.value)}
              placeholder="Describe what you built, architecture decisions, and results..."
              className="w-full h-24 bg-transparent hand-drawn-input resize-none text-base"
            />
          </div>
          <div className="flex justify-end pt-2">
            <button type="submit" className="ink-wash-btn-primary px-6 py-1.5 text-lg flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">add</span>
              <span>Add Project Artifact</span>
            </button>
          </div>
        </form>
      )}

      {/* Attached Evidence List */}
      <div className="mb-8">
        <h3 className="font-headline-sm text-lg text-on-surface mb-3 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-xl">inventory_2</span>
            <span>Attached Artifacts ({evidenceList.length})</span>
          </span>
          {evidenceList.length === 0 && (
            <span className="font-note-handwritten text-base text-tertiary">
              No artifacts attached yet (Agent will demand proof)
            </span>
          )}
        </h3>

        {evidenceList.length > 0 ? (
          <div className="space-y-2.5">
            {evidenceList.map((item, idx) => (
              <div
                key={idx}
                className="p-3.5 sketch-border-subtle bg-surface-container-low/90 flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="material-symbols-outlined text-primary text-2xl shrink-0">
                    {item.type === "file" ? "description" : item.type === "link" ? "link" : "code"}
                  </span>
                  <div className="min-w-0">
                    <p className="font-headline-sm text-base text-on-surface truncate font-medium">
                      {item.name}
                    </p>
                    <p className="font-body-md text-xs text-on-surface-variant truncate">
                      {item.description}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveItem(idx)}
                  className="text-error hover:text-error/80 p-1 transition-colors"
                  title="Remove artifact"
                >
                  <span className="material-symbols-outlined text-xl">delete</span>
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 sketch-border-subtle bg-surface-container-low/50 text-center">
            <p className="font-note-handwritten text-lg text-on-surface-variant">
              You can proceed without evidence, but the agent will enforce the zero-assumption rule and flag unverified claims.
            </p>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="flex justify-between items-center pt-4 border-t border-outline-variant/40">
        <button
          type="button"
          onClick={onBack}
          className="ink-wash-btn px-6 py-2 text-xl cursor-pointer"
        >
          Back
        </button>
        <button 
          type="button"
          onClick={() => onNext(evidenceList)}
          className="ink-wash-btn-primary px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer"
        >
          <span>{evidenceList.length > 0 ? `Continue with ${evidenceList.length} Artifacts` : "Skip for now"}</span>
          <span className="material-symbols-outlined text-sm">east</span>
        </button>
      </div>
    </motion.div>
  );
}
