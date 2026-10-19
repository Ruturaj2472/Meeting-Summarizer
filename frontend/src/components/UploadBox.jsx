import { useState } from 'react'

function UploadBox({ onSubmit }) {
  const [transcript, setTranscript] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  const handleSubmit = () => {
    if (transcript.trim().length < 50) return
    onSubmit(transcript)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => setIsDragging(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => setTranscript(ev.target.result)
    reader.readAsText(file)
  }

  const handleFileInput = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => setTranscript(ev.target.result)
    reader.readAsText(file)
  }

  return (
    <div className="w-full max-w-xl mx-auto flex flex-col items-center gap-8">

      <div className="flex flex-col items-center gap-4 text-center">
        <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center text-white text-2xl shadow-lg shadow-indigo-200">
          ✦
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">
            Turn meetings into action
          </h1>
          <p className="text-slate-500 text-sm mt-2 leading-relaxed">
            Upload a transcript and get AI-powered summaries,<br />
            action items, and follow-up emails instantly.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-center">
          {[
            { label: 'AI Summary', color: 'bg-indigo-500' },
            { label: 'Action Items', color: 'bg-green-500' },
            { label: 'Follow-up Draft', color: 'bg-amber-500' },
            { label: 'Reminders', color: 'bg-rose-500' },
          ].map(f => (
            <div key={f.label} className="flex items-center gap-1.5 text-xs text-slate-500 bg-white border border-slate-200 px-3 py-1 rounded-full">
              <div className={`w-1.5 h-1.5 rounded-full ${f.color}`} />
              {f.label}
            </div>
          ))}
        </div>
      </div>

      <div className="w-full bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-b border-dashed border-slate-200 p-6 text-center transition-colors cursor-pointer ${
            isDragging ? 'bg-indigo-50 border-indigo-300' : 'hover:bg-slate-50'
          }`}
        >
          <div className="text-3xl mb-2">📄</div>
          <p className="text-sm font-medium text-slate-600">
            Drop a transcript file here
          </p>
          <p className="text-xs text-slate-400 mt-1">Supports .txt and .vtt files</p>
          <label className="mt-2 inline-block cursor-pointer text-xs text-indigo-600 hover:text-indigo-800 underline">
            or browse to upload
            <input
              type="file"
              accept=".txt,.vtt"
              onChange={handleFileInput}
              className="hidden"
            />
          </label>
        </div>

        <div className="p-4">
          <p className="text-xs text-slate-400 mb-2">Or paste directly:</p>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste meeting transcript here..."
            rows={6}
            className="w-full text-sm border border-slate-200 rounded-xl p-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none placeholder:text-slate-300"
          />
          <div className="flex items-center justify-between mt-3">
            <span className="text-xs text-slate-400">
              {transcript.length} characters
              {transcript.length > 0 && transcript.length < 50 && (
                <span className="text-red-400 ml-1">(need at least 50)</span>
              )}
            </span>
            <button
              onClick={handleSubmit}
              disabled={transcript.trim().length < 50}
              className="bg-indigo-600 text-white px-5 py-2 rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Analyze transcript →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default UploadBox