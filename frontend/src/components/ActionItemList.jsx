import { useState } from 'react'

function ActionItemList({ items, onUpdate, meetingId, onAddItem }) {
  const [editingId, setEditingId] = useState(null)
  const [editText, setEditText] = useState('')
  const [remindStates, setRemindStates] = useState({})
  const [addingItem, setAddingItem] = useState(false)
  const [newItemText, setNewItemText] = useState('')
  const [newItemAssignee, setNewItemAssignee] = useState('')

  const handleStatusToggle = (item) => {
    const newStatus = item.status === 'pending' ? 'done' : 'pending'
    onUpdate(item.id, { status: newStatus })
  }

  const handleEditStart = (item) => {
    setEditingId(item.id)
    setEditText(item.text)
  }

  const handleEditSave = (item) => {
    if (editText.trim() === '') return
    onUpdate(item.id, { text: editText.trim() })
    setEditingId(null)
    setEditText('')
  }

  const handleEditCancel = () => {
    setEditingId(null)
    setEditText('')
  }

  const handleKeyDown = (e, item) => {
    if (e.key === 'Enter') handleEditSave(item)
    if (e.key === 'Escape') handleEditCancel()
  }

  const handleAddItem = () => {
    if (newItemText.trim() === '') return
    onAddItem(newItemText.trim(), newItemAssignee.trim() || null)
    setNewItemText('')
    setNewItemAssignee('')
    setAddingItem(false)
  }

  const handleAddKeyDown = (e) => {
    if (e.key === 'Escape') {
      setAddingItem(false)
      setNewItemText('')
      setNewItemAssignee('')
    }
  }

  const handleRemind = async (assignee) => {
    if (!meetingId) return
    setRemindStates(prev => ({ ...prev, [assignee]: 'loading' }))
    try {
      const res = await fetch(
        `/meetings/${meetingId}/remind/${encodeURIComponent(assignee)}`,
        { method: 'POST' }
      )
      if (!res.ok) {
        setRemindStates(prev => ({ ...prev, [assignee]: 'idle' }))
        return
      }
      const { subject, body } = await res.json()
      window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
      setRemindStates(prev => ({ ...prev, [assignee]: 'sent' }))
      setTimeout(() => {
        setRemindStates(prev => ({ ...prev, [assignee]: 'idle' }))
      }, 3000)
    } catch (err) {
      setRemindStates(prev => ({ ...prev, [assignee]: 'idle' }))
    }
  }

  const doneCount = items.filter(i => i.status === 'done').length
  const progressPct = items.length > 0
    ? Math.round((doneCount / items.length) * 100)
    : 0

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden animate-slide-up">

      {/* Header with progress */}
      <div className="px-4 py-3 border-b border-slate-100">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-slate-700">Action Items</h3>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            doneCount === items.length && items.length > 0
              ? 'bg-green-50 text-green-600'
              : 'bg-indigo-50 text-indigo-600'
          }`}>
            {doneCount}/{items.length} done
          </span>
        </div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Empty state */}
      {items.length === 0 && !addingItem && (
        <div className="p-8 text-center">
          <p className="text-slate-400 text-sm">No action items yet</p>
        </div>
      )}

      {/* Item list */}
      {items.length > 0 && (
        <ul className="divide-y divide-slate-100">
          {items.map((item, index) => (
            <li
              key={item.id}
              className="px-4 py-3 flex items-start gap-3 animate-slide-up"
              style={{
                animationDelay: `${index * 60}ms`,
                animationFillMode: 'both'
              }}
            >
              {/* Checkbox */}
              <button
                onClick={() => handleStatusToggle(item)}
                className={`mt-0.5 w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                  item.status === 'done'
                    ? 'bg-green-500 border-green-500'
                    : 'border-slate-300 hover:border-indigo-400'
                }`}
              >
                {item.status === 'done' && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>

              {/* Text + assignee */}
              <div className="flex-1 min-w-0">
                {editingId === item.id ? (
                  <div className="flex gap-2">
                    <input
                      autoFocus
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, item)}
                      className="flex-1 text-sm border border-indigo-400 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <button
                      onClick={() => handleEditSave(item)}
                      className="text-xs bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={handleEditCancel}
                      className="text-xs text-slate-500 px-2 py-1 rounded hover:bg-slate-100"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <p
                    onClick={() => handleEditStart(item)}
                    className={`text-sm cursor-pointer transition-colors ${
                      item.status === 'done'
                        ? 'line-through text-slate-400'
                        : 'text-slate-700 hover:text-indigo-600'
                    }`}
                  >
                    {item.text}
                  </p>
                )}

                {/* Assignee + remind */}
                {item.assignee &&
                  item.assignee !== 'null' &&
                  editingId !== item.id && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-400">
                      {item.assignee}
                    </span>
                    {item.status === 'pending' && meetingId && (() => {
                      const state = remindStates[item.assignee] || 'idle'
                      if (state === 'idle') return (
                        <button
                          onClick={() => handleRemind(item.assignee)}
                          className="flex items-center gap-1 text-xs text-slate-400 hover:text-indigo-500 transition-colors"
                        >
                          <span>✉</span>
                          <span>Remind</span>
                        </button>
                      )
                      if (state === 'loading') return (
                        <span className="flex items-center gap-1 text-xs text-indigo-500">
                          <span className="w-3 h-3 border border-indigo-400 border-t-transparent rounded-full animate-spin inline-block" />
                          Generating...
                        </span>
                      )
                      if (state === 'sent') return (
                        <span className="flex items-center gap-1 text-xs text-green-500 font-medium animate-pop-in">
                          ✓ Reminded
                        </span>
                      )
                    })()}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Add item section */}
      <div className="px-4 py-3 border-t border-slate-100">
        {addingItem ? (
          <div className="flex flex-col gap-2 animate-slide-up">
            <input
              autoFocus
              value={newItemText}
              onChange={(e) => setNewItemText(e.target.value)}
              onKeyDown={handleAddKeyDown}
              placeholder="What needs to be done?"
              className="w-full text-sm border border-indigo-400 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <input
              value={newItemAssignee}
              onChange={(e) => setNewItemAssignee(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAddItem()
                if (e.key === 'Escape') {
                  setAddingItem(false)
                  setNewItemText('')
                  setNewItemAssignee('')
                }
              }}
              placeholder="Assignee — optional (e.g. John)"
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <div className="flex gap-2">
              <button
                onClick={handleAddItem}
                disabled={newItemText.trim() === ''}
                className="text-xs bg-indigo-600 text-white px-3 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Add item
              </button>
              <button
                onClick={() => {
                  setAddingItem(false)
                  setNewItemText('')
                  setNewItemAssignee('')
                }}
                className="text-xs text-slate-500 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setAddingItem(true)}
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-indigo-600 transition-colors group"
          >
            <span className="w-4 h-4 rounded-full border-2 border-dashed border-slate-300 group-hover:border-indigo-400 flex items-center justify-center transition-colors">
              +
            </span>
            Add action item
          </button>
        )}
      </div>

    </div>
  )
}

export default ActionItemList