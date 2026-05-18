import { useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'

export default function ConversationSidebar({ conversations, onNew, onDelete }) {
  const navigate = useNavigate()
  const { id: activeId } = useParams()

  async function handleNew() {
    const title = `Conversation ${new Date().toLocaleDateString()}`
    const { data } = await api.post('/conversations', { title })
    onNew(data)
    navigate(`/chat/${data.id}`)
  }

  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-full">
      <div className="p-4 border-b border-gray-700">
        <button onClick={handleNew}
          className="w-full bg-blue-600 hover:bg-blue-700 py-2 px-4 rounded text-sm transition">
          + New Conversation
        </button>
      </div>
      <ul className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.map(conv => (
          <li key={conv.id}
            className={`flex items-center justify-between rounded px-3 py-2 cursor-pointer text-sm ${
              conv.id === activeId ? 'bg-gray-700' : 'hover:bg-gray-800'}`}
            onClick={() => navigate(`/chat/${conv.id}`)}>
            <span className="truncate flex-1">{conv.title}</span>
            <button onClick={e => { e.stopPropagation(); onDelete(conv.id) }}
              className="text-gray-500 hover:text-red-400 ml-2 text-xs">✕</button>
          </li>
        ))}
      </ul>
    </div>
  )
}
