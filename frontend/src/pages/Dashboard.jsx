import { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import api from '../api/client'
import ConversationSidebar from '../components/ConversationSidebar'
import DocumentUploader from '../components/DocumentUploader'
import DocumentList from '../components/DocumentList'
import ChatWindow from '../components/ChatWindow'

export default function Dashboard() {
  const [conversations, setConversations] = useState([])
  const [documents, setDocuments] = useState([])

  useEffect(() => {
    api.get('/conversations').then(r => setConversations(r.data.content || []))
    api.get('/documents').then(r => setDocuments(r.data.content || []))
  }, [])

  async function handleDeleteConv(id) {
    await api.delete(`/conversations/${id}`)
    setConversations(prev => prev.filter(c => c.id !== id))
  }

  const readyDocs = documents.filter(d => d.status === 'READY')

  return (
    <div className="flex h-screen">
      <ConversationSidebar
        conversations={conversations}
        onNew={conv => setConversations(prev => [conv, ...prev])}
        onDelete={handleDeleteConv} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Routes>
          <Route path="/" element={
            <div className="p-8 max-w-2xl mx-auto w-full">
              <h2 className="text-xl font-bold text-gray-800 mb-4">Documents</h2>
              <DocumentUploader onUploadComplete={doc => setDocuments(prev => [doc, ...prev])} />
              <DocumentList documents={documents} onDelete={id => setDocuments(prev => prev.filter(d => d.id !== id))} />
            </div>
          } />
          <Route path="/chat/:id" element={<ChatWindow availableDocs={readyDocs} />} />
        </Routes>
      </div>
    </div>
  )
}
