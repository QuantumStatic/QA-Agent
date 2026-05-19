import { useState } from 'react'
import api from '../api/client'

export default function DocumentList({ documents, onDelete }) {
  const [deleting, setDeleting] = useState(null)

  async function handleDelete(docId) {
    setDeleting(docId)
    try {
      await api.delete(`/documents/${docId}`)
      onDelete(docId)
    } finally {
      setDeleting(null)
    }
  }

  if (!documents.length) return (
    <p className="text-gray-400 text-sm mt-4">No documents uploaded yet.</p>
  )

  return (
    <ul className="mt-4 space-y-2">
      {documents.map(doc => (
        <li key={doc.id} className="flex items-center justify-between bg-gray-50 rounded px-3 py-2">
          <div>
            <p className="text-sm font-medium text-gray-700 truncate max-w-xs">{doc.filename}</p>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              doc.status === 'READY' ? 'bg-green-100 text-green-700' :
              doc.status === 'PROCESSING' ? 'bg-yellow-100 text-yellow-700' :
              'bg-red-100 text-red-700'}`}>{doc.status}</span>
          </div>
          <button onClick={() => handleDelete(doc.id)} disabled={deleting === doc.id}
            className="text-red-400 hover:text-red-600 text-sm ml-4 disabled:opacity-50">
            {deleting === doc.id ? '...' : 'Delete'}
          </button>
        </li>
      ))}
    </ul>
  )
}
