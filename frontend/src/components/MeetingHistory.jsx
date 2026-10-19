import { useState } from 'react'

function MeetingHistory({ meetings, onSelect, activeMeetingId, onDelete }) {
  const [hoveredId, setHoveredId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric'
    })
  }

  const getCompletion = (meeting) => {
    const items = meeting.action_items || []
    const done = items.filter(i => i.status === 'done').length
    return { done, total: items.length }
  }

const handleDelete = async (e, meetingId) => {
  e.stopPropagation()
  if (!window.confirm('Delete this meeting? This cannot be undone.')) return
  setDeletingId(meetingId)
  try {
    const res = await fetch(`/meetings/${meetingId}`, {
      method: 'DELETE'
    })
    if (!res.ok) {
      const err = await res.json()
      alert(`Failed to delete: ${err.detail}`)
      return
    }
    onDelete(meetingId)
  } catch (err) {
    alert('Failed to delete meeting')
  } finally {
    setDeletingId(null)
  }
}

  return (
    <div className="flex-1 overflow-y-auto px-3 pb-4">
      {meetings.length === 0 ? (
        <p className="text-xs text-slate-600 text-center mt-8 px-2 leading-relaxed">
          No meetings yet. Upload your first transcript.
        </p>
      ) : (
        <>
          <p className="text-xs font-semibold text-slate-600 uppercase tracking-widest px-2 mb-2">
            Recent
          </p>
          <ul className="flex flex-col gap-0.5">
            {meetings.map(meeting => {
              const { done, total } = getCompletion(meeting)
              const isActive = meeting.id === activeMeetingId
              const allDone = total > 0 && done === total
              const isHovered = hoveredId === meeting.id
              const isDeleting = deletingId === meeting.id

              return (
                <li key={meeting.id}>
                  <div
                    className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors flex items-start gap-1 group cursor-pointer ${
                      isActive
                        ? 'bg-slate-700'
                        : 'hover:bg-slate-800'
                    }`}
                    onMouseEnter={() => setHoveredId(meeting.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => onSelect(meeting)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs font-medium truncate ${
                        isActive ? 'text-slate-100' : 'text-slate-400'
                      }`}>
                        {meeting.title}
                      </p>
                      <div className="flex items-center justify-between mt-1">
                        <p className="text-xs text-slate-600">
                          {formatDate(meeting.created_at)}
                        </p>
                        {total > 0 && (
                          <span className={`text-xs font-medium ${
                            allDone ? 'text-green-500' : 'text-indigo-400'
                          }`}>
                            {done}/{total}
                          </span>
                        )}
                      </div>
                    </div>

                    {(isHovered || isActive) && (
                      <button
                        onClick={(e) => handleDelete(e, meeting.id)}
                        className="flex-shrink-0 w-5 h-5 flex items-center justify-center text-slate-600 hover:text-red-400 transition-colors mt-0.5 animate-fade-in"
                        title="Delete meeting"
                      >
                        {isDeleting ? (
                          <span className="w-3 h-3 border border-slate-500 border-t-transparent rounded-full animate-spin" />
                        ) : '✕'}
                      </button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </>
      )}
    </div>
  )
}

export default MeetingHistory