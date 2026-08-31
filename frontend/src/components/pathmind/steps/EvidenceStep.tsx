"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { UploadCloud, CheckCircle2 } from "lucide-react";
import { useState } from "react";

interface EvidenceStepProps {
  onNext: () => void;
  onBack: () => void;
}

export function EvidenceStep({ onNext, onBack }: EvidenceStepProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);

  const handleUploadClick = () => {
    setIsUploading(true);
    // Simulate upload delay
    setTimeout(() => {
      setIsUploading(false);
      setUploaded(true);
    }, 1500);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="max-w-2xl mx-auto px-4 py-8"
    >
      <div className="mb-10">
        <h2 className="text-3xl font-medium tracking-tight mb-3">Any background evidence?</h2>
        <p className="text-slate-500 dark:text-slate-400">
          Upload resumes, transcripts, or portfolios. PATHMIND will extract relevant skills to personalize your roadmap.
        </p>
      </div>

      <div className="mb-12">
        <button
          onClick={handleUploadClick}
          disabled={isUploading || uploaded}
          className={`
            w-full h-64 border-2 border-dashed rounded-3xl flex flex-col items-center justify-center transition-all duration-300
            ${uploaded 
              ? 'border-emerald-500/50 bg-emerald-500/5 dark:bg-emerald-500/10' 
              : 'border-slate-300 dark:border-slate-700 hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/50'}
          `}
        >
          {uploaded ? (
            <motion.div 
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex flex-col items-center text-emerald-600 dark:text-emerald-400"
            >
              <CheckCircle2 className="w-12 h-12 mb-4" />
              <p className="font-medium text-lg">Evidence attached</p>
              <p className="text-sm opacity-80 mt-1">Ready for synthesis</p>
            </motion.div>
          ) : isUploading ? (
            <div className="flex flex-col items-center text-indigo-500">
              <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
              <p className="font-medium text-lg">Analyzing documents...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-slate-500 dark:text-slate-400">
              <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-full mb-4 group-hover:scale-110 transition-transform">
                <UploadCloud className="w-8 h-8" />
              </div>
              <p className="font-medium text-lg text-slate-900 dark:text-slate-200">Click to upload files</p>
              <p className="text-sm mt-1">PDF, DOCX, or TXT</p>
            </div>
          )}
        </button>
      </div>

      <div className="flex justify-between items-center">
        <Button variant="ghost" onClick={onBack} className="text-slate-500">Back</Button>
        <Button 
          onClick={onNext}
          className="bg-indigo-600 hover:bg-indigo-500 min-w-[120px] rounded-full"
        >
          {uploaded ? 'Continue' : 'Skip for now'}
        </Button>
      </div>
    </motion.div>
  );
}
