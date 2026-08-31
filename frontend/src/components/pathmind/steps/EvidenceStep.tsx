"use client";

import { motion } from "framer-motion";
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
    setTimeout(() => {
      setIsUploading(false);
      setUploaded(true);
    }, 1200);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="max-w-2xl mx-auto px-4 py-8"
    >
      <div className="mb-8 text-center">
        <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 mb-2 inline-block">
          Evidence Scribing
        </span>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">
          Any background evidence?
        </h2>
        <p className="font-body-md text-on-surface-variant">
          Attach project repositories, transcripts, or portfolios to ground your career counseling synthesis.
        </p>
      </div>

      <div className="mb-10">
        <button
          type="button"
          onClick={handleUploadClick}
          disabled={isUploading || uploaded}
          className={`
            w-full h-60 p-8 sketch-border flex flex-col items-center justify-center transition-all duration-300 cursor-pointer
            ${uploaded 
              ? 'border-primary bg-primary-fixed/30 shadow-md' 
              : 'border-[#424842] hover:bg-surface-container-high/60 bg-surface-container-low/70'}
          `}
        >
          {uploaded ? (
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex flex-col items-center text-primary"
            >
              <div className="w-14 h-14 rounded-full border-2 border-primary bg-primary/20 flex items-center justify-center mb-3">
                <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  check_circle
                </span>
              </div>
              <p className="font-headline-sm text-xl text-on-surface">Observable Evidence Attached</p>
              <p className="font-note-handwritten text-xl text-primary mt-1">4 mobile repositories & engineering samples cataloged</p>
            </motion.div>
          ) : isUploading ? (
            <div className="flex flex-col items-center text-secondary">
              <span className="material-symbols-outlined text-4xl animate-spin mb-3">
                progress_activity
              </span>
              <p className="font-headline-sm text-lg text-on-surface">Reading and analyzing artifacts...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-on-surface-variant">
              <div className="w-14 h-14 rounded-full border border-outline/40 bg-surface-container flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                <span className="material-symbols-outlined text-3xl text-secondary">
                  attach_file
                </span>
              </div>
              <p className="font-headline-sm text-xl text-on-surface">Click to attach portfolio or resume</p>
              <p className="font-note-handwritten text-lg text-on-surface-variant mt-1">PDF, markdown, code repos, or transcript</p>
            </div>
          )}
        </button>
      </div>

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
          onClick={onNext}
          className="ink-wash-btn-primary px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer"
        >
          <span>{uploaded ? 'Continue' : 'Skip for now'}</span>
          <span className="material-symbols-outlined text-sm">east</span>
        </button>
      </div>
    </motion.div>
  );
}
