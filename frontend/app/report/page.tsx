"use client";

import { AlertTriangle, Send } from "lucide-react";

export default function ReportPage() {
  return (
    <div className="max-w-3xl mx-auto w-full p-6 flex flex-col gap-6">
      <div className="bg-slate-800 p-6 rounded-lg border border-slate-700 shadow-xl">
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2 mb-2">
          <AlertTriangle className="w-6 h-6 text-amber-400" />
          Submit Community Safety Report
        </h1>
        <p className="text-sm text-slate-400 mb-6">
          Report safety hazards (poor lighting, lack of CCTV, harassment risk). Submissions are verified by Gemini LLM before updating route scores.
        </p>

        <form className="flex flex-col gap-4" onSubmit={(e) => e.preventDefault()}>
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Location / Landmark (West India)</label>
            <input
              type="text"
              placeholder="e.g. Dadar Station West Flyover, Mumbai"
              className="w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-sm text-slate-100 focus:outline-none focus:border-amber-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Hazard Description</label>
            <textarea
              rows={4}
              placeholder="Describe the issue in detail (e.g., streetlight out near corner, isolated walkway with no crowd)..."
              className="w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-sm text-slate-100 focus:outline-none focus:border-amber-500"
            />
          </div>

          <button className="bg-amber-600 hover:bg-amber-500 text-white font-medium py-2.5 px-4 rounded flex items-center justify-center gap-2 transition-colors text-sm shadow-lg">
            <Send className="w-4 h-4" /> Submit Report for Gemini Verification
          </button>
        </form>
      </div>
    </div>
  );
}

