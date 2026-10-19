import { useState, useEffect } from 'react'
import UploadBox from './components/UploadBox'
import ActionItemList from './components/ActionItemList'
import EmailPreview from './components/EmailPreview'
import MeetingHistory from './components/MeetingHistory'
import SummaryCard from './components/SummaryCard'
import Toast from './components/Toast'
import ProcessingScreen from './components/ProcessingScreen'

const TABS = ['Summary', 'Action Items', 'Follow-up Draft']

function App() {
  const [appState, setAppState] = useState('idle')
  const [meetingData, setMeetingData] = useState(null)
  const [actionItems, setActionItems] = useState([])
  const [emailDraft, setEmailDraft] = useState(null)
  const [summary, setSummary] = useState(null)
  const [meetings, setMeetings] = useState([])
  const [toast, setToast] = useState(null)
  const [activeTab, setActiveTab] = useState('Summary')
  const [typedTitle, setTypedTitle] = useState('')
  const [titleDone, setTitleDone] = useState(false)
  const [remindAllState, setRemindAllState] = useState('idle')

  useEffect(() => { fetchMeetings() }, [])

  useEffect(() => {
    if (appState === 'done' && meetingData?.title) {
      setTypedTitle('')
      setTitleDone(false)
      setActiveTab('Summary')
      const title = meetingData.title
      let i = 0
      const interval = setInterval(() => {
        i++
        setTypedTitle(title.slice(0, i))
        if (i >= title.length) {
          clearInterval(interval)
          setTitleDone(true)
        }
      }, 40)
      return () => clearInterval(interval)
    }
  }, [appState, meetingData])

  const showToast = (message, type = 'success') => setToast({ message, type })

  const fetchMeetings = async () => {
  try {
    const res = await fetch('/meetings')
    const data = await res.json()
    setMeetings(Array.isArray(data) ? data : [])
  } catch (err) {
    console.error('Failed to fetch meetings:', err)
    setMeetings([])
  }
}

  const handleTranscriptSubmit = async (transcript) => {
    setAppState('loading')
    try {
      const res = await fetch('/meetings/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript })
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail)
      }
      const data = await res.json()
      setMeetingData(data.meeting)
      setActionItems(data.action_items)
      setEmailDraft(data.email_draft)
      setSummary(data.summary)
      setAppState('done')
      fetchMeetings()
      showToast('Meeting analysed successfully')
    } catch (err) {
      showToast(err.message, 'error')
      setAppState('idle')
    }
  }

  const handleActionItemUpdate = async (id, updates) => {
  try {
    const params = new URLSearchParams(updates).toString()
    const res = await fetch(`/action-items/${id}?${params}`, {
      method: 'PATCH',
    })
    const updated = await res.json()

    const newItems = actionItems.map(item =>
      item.id === updated.id ? updated : item
    )
    setActionItems(newItems)

    if (meetingData?.id) {
      setMeetings(prev => prev.map(m => {
        if (m.id !== meetingData.id) return m
        return {
          ...m,
          action_items: newItems
        }
      }))
    }

    if (updates.status) {
      showToast(
        updates.status === 'done' ? 'Marked as done' : 'Marked as pending',
        'info'
      )
    }
  } catch (err) {
    showToast('Failed to update item', 'error')
  }
}

  const handleAddItem = async (text, assignee) => {
  if (!meetingData?.id) return
  try {
    const params = new URLSearchParams({ meeting_id: meetingData.id, text })
    if (assignee) params.append('assignee', assignee)
    const res = await fetch(`/action-items?${params.toString()}`, {
      method: 'POST'
    })
    const newItem = await res.json()
    const newItems = [...actionItems, newItem]
    setActionItems(newItems)

    setMeetings(prev => prev.map(m => {
      if (m.id !== meetingData.id) return m
      return {
        ...m,
        action_items: newItems
      }
    }))

    showToast('Action item added')
  } catch (err) {
    showToast('Failed to add item', 'error')
  }
}

  const handleMeetingSelect = (meeting) => {
    setMeetingData(meeting)
    setActionItems(meeting.action_items)
    setEmailDraft(null)
    setSummary(meeting.summary || null)
    setAppState('done')
    setActiveTab('Summary')
    setRemindAllState('idle')
  }

 const handleDelete = (meetingId) => {
  setMeetings(prev => prev.filter(m => m.id !== meetingId))

  if (meetingData?.id === meetingId) {
    setAppState('idle')
    setMeetingData(null)
    setActionItems([])
    setEmailDraft(null)
    setSummary(null)
    setTypedTitle('')
    setTitleDone(false)
    setRemindAllState('idle')
    showToast('Meeting deleted — you were viewing this meeting', 'info')
  } else {
    showToast('Meeting deleted', 'info')
  }
}

  const handleRemindAll = async () => {
    if (!meetingData?.id) return
    setRemindAllState('loading')
    try {
      const res = await fetch(
        `/meetings/${meetingData.id}/remind-all`,
        { method: 'POST' }
      )
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail)
      }
      const { subject, body } = await res.json()
      window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
      setRemindAllState('sent')
      showToast('Reminder email ready')
      setTimeout(() => setRemindAllState('idle'), 3000)
    } catch (err) {
      showToast(err.message || 'Failed to generate reminder', 'error')
      setRemindAllState('idle')
    }
  }

  const handleExport = () => {
    if (!meetingData) return

    const pendingItems = actionItems.filter(i => i.status === 'pending')
    const doneItems = actionItems.filter(i => i.status === 'done')

    const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${meetingData.title} — Meeting Report</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; color: #1e293b; }
    h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
    .date { font-size: 13px; color: #64748b; margin-bottom: 32px; }
    h2 { font-size: 14px; font-weight: 600; color: #6366f1; text-transform: uppercase; letter-spacing: .05em; margin: 28px 0 10px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }
    p { font-size: 14px; line-height: 1.7; color: #475569; margin: 0 0 12px; }
    ul { margin: 0; padding-left: 20px; }
    li { font-size: 14px; color: #475569; margin-bottom: 6px; line-height: 1.5; }
    .done { text-decoration: line-through; color: #94a3b8; }
    .assignee { font-size: 12px; color: #94a3b8; margin-left: 4px; }
    .decisions { background: #f8fafc; border-left: 3px solid #6366f1; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-top: 8px; }
    .footer { margin-top: 48px; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 16px; }
  </style>
</head>
<body>
  <h1>${meetingData.title}</h1>
  <div class="date">${new Date(meetingData.created_at).toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  })}</div>

  ${summary ? `
  <h2>Meeting Summary</h2>
  <p>${summary.overview || ''}</p>
  ${summary.key_points?.length > 0 ? `
  <strong style="font-size:13px;color:#334155">Key Points</strong>
  <ul>${summary.key_points.map(p => `<li>${p}</li>`).join('')}</ul>
  ` : ''}
  ${summary.decisions ? `
  <div class="decisions">
    <strong style="font-size:13px">Decisions Made</strong>
    <p style="margin-top:6px;margin-bottom:0">${summary.decisions}</p>
  </div>
  ` : ''}
  ` : ''}

  <h2>Action Items</h2>
  ${pendingItems.length > 0 ? `
  <strong style="font-size:12px;color:#64748b">Pending</strong>
  <ul>${pendingItems.map(i => `
    <li>${i.text}${i.assignee && i.assignee !== 'null'
      ? `<span class="assignee">— ${i.assignee}</span>`
      : ''
    }</li>`).join('')}
  </ul>
  ` : '<p style="color:#94a3b8;font-size:13px">All action items completed!</p>'}

  ${doneItems.length > 0 ? `
  <strong style="font-size:12px;color:#64748b">Completed</strong>
  <ul>${doneItems.map(i => `<li class="done">${i.text}</li>`).join('')}</ul>
  ` : ''}

  <div class="footer">Generated by MeetingAI · ${new Date().toLocaleDateString()}</div>
</body>
</html>`

    const win = window.open('', '_blank')
    win.document.write(html)
    win.document.close()
    win.print()
    showToast('Report exported')
  }

  return (
    <div className="min-h-screen flex bg-slate-950">

      <aside className="w-60 bg-slate-900 flex flex-col flex-shrink-0 border-r border-slate-800">
        <div className="px-4 pt-5 pb-4">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
              ✦
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-100 tracking-tight">MeetingAI</p>
              <p className="text-xs text-slate-500">Powered by GPT-4o</p>
            </div>
          </div>
          <button
            onClick={() => {
              setAppState('idle')
              setMeetingData(null)
              setSummary(null)
              setEmailDraft(null)
              setActionItems([])
            }}
            className="w-full py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <span>+</span> New meeting
          </button>
        </div>

        <MeetingHistory
          meetings={meetings}
          onSelect={handleMeetingSelect}
          activeMeetingId={meetingData?.id}
          onDelete={handleDelete}
        />
      </aside>

      <div className="flex-1 flex flex-col bg-slate-50 min-h-screen">

        {appState === 'done' && (
          <>
            <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
              <div>
                <div className="flex items-center gap-1">
                  <h1 className="text-base font-semibold text-slate-800 overflow-hidden whitespace-nowrap">
                    {typedTitle}
                  </h1>
                  {!titleDone && (
                    <span className="inline-block w-0.5 h-4 bg-indigo-500 animate-blink ml-0.5" />
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {meetingData?.created_at
                    ? new Date(meetingData.created_at).toLocaleDateString('en-US', {
                        weekday: 'long', month: 'long', day: 'numeric'
                      })
                    : ''}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleExport}
                  className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  ↓ Export report
                </button>
                <button
                  onClick={handleRemindAll}
                  disabled={remindAllState !== 'idle'}
                  className={`flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg font-medium transition-colors disabled:opacity-60 ${
                    remindAllState === 'sent'
                      ? 'bg-green-50 text-green-600 border border-green-200'
                      : 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100'
                  }`}
                >
                  {remindAllState === 'loading' && (
                    <span className="w-3 h-3 border border-amber-400 border-t-transparent rounded-full animate-spin" />
                  )}
                  {remindAllState === 'sent' ? '✓ Reminders ready' : '✉ Remind all'}
                </button>
              </div>
            </div>

            <div className="bg-white border-b border-slate-200 px-6 flex-shrink-0">
              <div className="flex gap-0">
                {TABS.map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab
                        ? 'border-indigo-600 text-indigo-600'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        <main className="flex-1 overflow-y-auto">

          {appState === 'idle' && (
            <div className="h-full flex items-center justify-center p-6">
              <UploadBox onSubmit={handleTranscriptSubmit} />
            </div>
          )}

          {appState === 'loading' && <ProcessingScreen />}

          {appState === 'done' && (
            <div className="max-w-2xl mx-auto p-6">

              {activeTab === 'Summary' && summary && (
                <SummaryCard summary={summary} />
              )}

              {activeTab === 'Summary' && !summary && (
                <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
                  <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center text-2xl">
                    📋
                  </div>
                  <div>
                    <p className="text-slate-600 font-medium text-sm">
                      No summary for this meeting
                    </p>
                    <p className="text-slate-400 text-xs mt-1 max-w-xs leading-relaxed">
                      This meeting was processed before summaries were added.
                      Re-process the transcript to generate one.
                    </p>
                  </div>
                </div>
              )}

              {activeTab === 'Action Items' && (
                <ActionItemList
                  items={actionItems}
                  onUpdate={handleActionItemUpdate}
                  meetingId={meetingData?.id}
                  onAddItem={handleAddItem}
                />
              )}

              {activeTab === 'Follow-up Draft' && emailDraft && (
  <EmailPreview
    draft={emailDraft}
    meetingId={meetingData?.id}
    onCopy={() => showToast('Email copied to clipboard')}
    onExport={handleExport}
  />
)}

              {activeTab === 'Follow-up Draft' && !emailDraft && (
  <div className="bg-white rounded-xl border border-slate-200 overflow-hidden animate-slide-up">
    <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
      <h3 className="text-sm font-semibold text-slate-700">Follow-up Draft</h3>
    </div>
    <div className="px-4 py-3 bg-amber-50 border-b border-amber-100 flex items-start gap-2">
      <span className="text-amber-500 text-sm flex-shrink-0 mt-0.5">ℹ</span>
      <p className="text-xs text-amber-700 leading-relaxed">
        No draft was generated for this meeting yet. Click <strong>Generate draft</strong> to create one based on the current action items.
      </p>
    </div>
    <div className="p-8 flex flex-col items-center gap-4">
      <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center text-2xl">
        ✉️
      </div>
      <div className="text-center">
        <p className="text-slate-600 font-medium text-sm">No follow-up draft yet</p>
        <p className="text-slate-400 text-xs mt-1 max-w-xs leading-relaxed">
          Generate a draft based on the current action items and meeting summary.
        </p>
      </div>
      <div className="flex gap-3">
        <button
          onClick={async () => {
            if (!meetingData?.id) return
            setRemindAllState('loading')
            try {
              const res = await fetch(
                `/meetings/${meetingData.id}/regenerate-email`,
                { method: 'POST' }
              )
              const data = await res.json()
              setEmailDraft(data)
              showToast('Follow-up draft generated')
            } catch (err) {
              showToast('Failed to generate draft', 'error')
            } finally {
              setRemindAllState('idle')
            }
          }}
          disabled={remindAllState !== 'idle'}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {remindAllState === 'loading' ? (
            <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : '✉'}
          Generate draft
        </button>
        <button
          onClick={handleRemindAll}
          disabled={remindAllState !== 'idle'}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 rounded-lg transition-colors disabled:opacity-60"
        >
          {remindAllState === 'loading' ? (
            <span className="w-3 h-3 border border-amber-400 border-t-transparent rounded-full animate-spin" />
          ) : '✉'}
          Remind all
        </button>
      </div>
    </div>
  </div>
)}

            </div>
          )}

        </main>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

    </div>
  )
}

export default App