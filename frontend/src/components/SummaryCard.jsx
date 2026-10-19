import { useState } from 'react'

function SummaryCard({ summary }) {
  return (
    <div className="flex flex-col gap-4 animate-slide-up">
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-indigo-500" />
          <span className="text-sm font-semibold text-slate-700">Meeting Summary</span>
          <span className="ml-auto text-xs px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded-full font-medium">
            AI Generated
          </span>
        </div>
        <div className="p-4 flex flex-col gap-4">
          <p className="text-sm text-slate-600 leading-relaxed">
            {summary.overview}
          </p>

          {summary.key_points?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                Key points
              </p>
              <ul className="flex flex-col gap-2">
                {summary.key_points.map((point, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 flex-shrink-0 mt-1.5" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.decisions && (
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
                Decisions made
              </p>
              <p className="text-sm text-slate-600 leading-relaxed">
                {summary.decisions}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SummaryCard