"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, Send, CheckCircle2, XCircle, Sparkles, MapPin, Tag, ShieldAlert, RefreshCw } from "lucide-react";

interface EvaluationResult {
  report_id: string;
  status: string;
  is_trustworthy: boolean;
  credibility_score: number;
  reasoning: string;
  safety_impact_applied: number;
  report_details: any;
}

export default function ReportPage() {
  const [locationLandmark, setLocationLandmark] = useState("Dadar Station West Flyover, Mumbai");
  const [reportType, setReportType] = useState("poor_lighting");
  const [description, setDescription] = useState("Streetlight out near the corner flyover, dark walkway with low crowd density after 9 PM.");
  const [submitting, setSubmitting] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [recentReports, setRecentReports] = useState<any[]>([]);
  const [loadingReports, setLoadingReports] = useState(false);

  const fetchRecentReports = async () => {
    setLoadingReports(true);
    try {
      const res = await fetch("http://localhost:8000/api/reports/list");
      if (res.ok) {
        const data = await res.json();
        setRecentReports(data.reports || []);
      }
    } catch (err) {
      console.error("Failed to load reports:", err);
    } finally {
      setLoadingReports(false);
    }
  };

  useEffect(() => {
    fetchRecentReports();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    setEvalResult(null);

    try {
      const res = await fetch("http://localhost:8000/api/reports/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          location_landmark: locationLandmark,
          report_type: reportType,
          description: description,
          user_id: "user_web_app",
          segment_id: "seg-mh-1001",
        }),
      });

      if (!res.ok) {
        throw new Error(`Submission failed with status HTTP ${res.status}`);
      }

      const data: EvaluationResult = await res.json();
      setEvalResult(data);
      fetchRecentReports(); // Refresh recent list
    } catch (err: any) {
      console.error("Report submit error:", err);
      setErrorMsg(err.message || "Failed to submit report. Please verify backend is running on port 8000.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full p-6 flex flex-col gap-6">
      {/* Header Panel */}
      <div className="glass-panel p-6 rounded-xl shadow-xl">
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2 mb-2">
          <AlertTriangle className="w-6 h-6 text-amber-400" />
          Community Safety Report & Gemini Trust Filter
        </h1>
        <p className="text-sm text-slate-400">
          Report active hazards (poor lighting, harassment risk, CCTV outage). Submissions are evaluated in real-time by Google Gemini 2.5 Flash LLM to filter spam and prioritize authentic local safety warnings.
        </p>

        {/* Report Submission Form */}
        <form className="flex flex-col gap-4 mt-6" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1 block">Location / Landmark (West India)</label>
              <div className="relative">
                <MapPin className="w-4 h-4 text-amber-400 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={locationLandmark}
                  onChange={(e) => setLocationLandmark(e.target.value)}
                  placeholder="e.g. Dadar Station West Flyover, Mumbai"
                  className="w-full glass-inset rounded-lg p-2.5 pl-9 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1 block">Hazard Category</label>
              <div className="relative">
                <Tag className="w-4 h-4 text-amber-500 absolute left-3 top-3 z-10" />
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="w-full rounded-lg p-2.5 pl-9 text-sm text-black font-medium focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20 bg-white border border-slate-300 shadow-sm"
                >
                  <option value="poor_lighting" className="text-black bg-white font-medium">💡 Dark / Unlit Streetlight</option>
                  <option value="harassment_risk" className="text-black bg-white font-medium">⚠️ Harassment / Eve-Teasing Risk</option>
                  <option value="cctv_broken" className="text-black bg-white font-medium">📷 Broken / Missing CCTV Camera</option>
                  <option value="isolated_area" className="text-black bg-white font-medium">🏚️ Deserted / Isolated Walkway</option>
                </select>
              </div>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1 block">Detailed Hazard Description</label>
            <textarea
              rows={3}
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the issue with specific details (e.g. broken street lamp on corner of Gokhale Road, dark path between 8 PM and midnight)..."
              className="w-full glass-inset rounded-lg p-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="bg-gradient-to-r from-teal-500 to-pink-500 hover:from-teal-400 hover:to-pink-400 text-slate-950 font-semibold py-2.5 px-5 rounded-lg flex items-center justify-center gap-2 transition-all text-sm shadow-lg shadow-pink-950/50 w-fit disabled:opacity-50"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></span>
                Gemini LLM Verifying Report...
              </span>
            ) : (
              <>
                <Send className="w-4 h-4" /> Submit Report for Gemini Verification
              </>
            )}
          </button>
        </form>

        {errorMsg && (
          <div className="bg-rose-950/80 border border-rose-800 text-rose-300 p-3 rounded-lg text-xs mt-4">
            {errorMsg}
          </div>
        )}

        {/* Gemini Trust Verification Result Card */}
        {evalResult && (
          <div className={`mt-6 p-4 rounded-xl border flex flex-col gap-3 transition-all ${
            evalResult.is_trustworthy
              ? "bg-emerald-950/60 border-emerald-600/80 text-emerald-100"
              : "bg-rose-950/60 border-rose-600/80 text-rose-100"
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-bold text-base">
                {evalResult.is_trustworthy ? (
                  <>
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    <span>Report Approved & Verified</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5 text-rose-400" />
                    <span>Report Flagged / Low Trust</span>
                  </>
                )}
              </div>

              <div className="flex items-center gap-1 text-xs font-mono px-2.5 py-1 rounded bg-slate-900 border border-slate-700">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span>Credibility:</span>
                <span className="font-bold text-amber-300">
                  {Math.round(evalResult.credibility_score * 100)}%
                </span>
              </div>
            </div>

            <p className="text-xs leading-relaxed bg-slate-900/80 p-3 rounded-lg border border-slate-700 font-sans">
              <strong className="text-slate-300 block mb-0.5">Gemini LLM Filter Reasoning:</strong>
              {evalResult.reasoning}
            </p>

            {evalResult.is_trustworthy && evalResult.safety_impact_applied !== 0 && (
              <div className="text-xs font-mono text-emerald-300">
                ⚡ Applied Safety Penalty: <strong>{evalResult.safety_impact_applied} pts</strong> to street segment safety weight.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Feed of Recent Reports */}
      <div className="glass-panel p-6 rounded-xl shadow-xl flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-emerald-400" />
            Verified Community Feed ({recentReports.length})
          </h2>
          <button
            onClick={fetchRecentReports}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 font-mono"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingReports ? "animate-spin" : ""}`} /> Refresh Feed
          </button>
        </div>

        {recentReports.length === 0 ? (
          <p className="text-xs text-slate-400 italic">No community reports submitted yet in this session.</p>
        ) : (
          <div className="flex flex-col gap-3 max-h-72 overflow-y-auto pr-1">
            {recentReports.map((rep, idx) => (
              <div key={rep.id || idx} className="glass-inset p-3 rounded-lg flex flex-col gap-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-amber-400" />
                    {rep.location_landmark}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    rep.status === "approved" ? "bg-emerald-950 text-emerald-300 border border-emerald-800" : "bg-rose-950 text-rose-300 border border-rose-800"
                  }`}>
                    {rep.status}
                  </span>
                </div>
                <p className="text-slate-300">{rep.description}</p>
                <div className="text-[10px] text-slate-400 font-mono mt-1 flex justify-between">
                  <span>Type: {rep.report_type}</span>
                  <span>Credibility Score: {Math.round((rep.credibility_score || 0) * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

