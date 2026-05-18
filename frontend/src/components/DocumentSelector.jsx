import { useState, useRef, useEffect } from 'react'

export default function DocumentSelector({ docs = [], selected, onChange }) {
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef(null)

  useEffect(() => {
    if (!open) return
    function handleOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [open])

  if (!docs.length) {
    return <span className="text-sm text-gray-400">No documents ready</span>
  }

  function toggle(id) {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onChange(next)
  }

  function selectAll() {
    onChange(new Set(docs.map(d => d.id)))
  }

  function clearAll() {
    onChange(new Set())
  }

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        onClick={() => setOpen(o => !o)}
        className="text-sm border border-gray-300 rounded px-3 py-1.5 bg-white hover:bg-gray-50 flex items-center gap-1"
      >
        Documents ({selected.size})
        <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
            <button onClick={selectAll} className="text-xs text-blue-600 hover:underline">Select all</button>
            <button onClick={clearAll} className="text-xs text-gray-500 hover:underline">Clear</button>
          </div>
          <div className="max-h-56 overflow-y-auto py-1">
            {docs.map(doc => (
              <label key={doc.id} className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selected.has(doc.id)}
                  onChange={() => toggle(doc.id)}
                  className="flex-shrink-0"
                />
                <span className="text-sm text-gray-700 truncate" title={doc.filename}>
                  {doc.filename}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
