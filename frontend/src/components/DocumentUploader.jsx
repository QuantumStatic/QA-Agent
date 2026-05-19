import { useState, useRef } from 'react'
import api from '../api/client'

export default function DocumentUploader({ onUploadComplete }) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef()

  async function handleFile(file) {
    if (!file || file.type !== 'application/pdf') {
      setError('Only PDF files are accepted')
      return
    }
    if (file.size > 25 * 1024 * 1024) {
      setError('File exceeds 25MB limit')
      return
    }
    setError('')
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      onUploadComplete(data)
    } catch {
      setError('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-blue-400 transition"
      onClick={() => inputRef.current?.click()}
      onDragOver={e => e.preventDefault()}
      onDrop={e => { e.preventDefault(); handleFile(e.dataTransfer.files[0]) }}>
      <input ref={inputRef} type="file" accept=".pdf" className="hidden"
        onChange={e => handleFile(e.target.files[0])} />
      {uploading
        ? <p className="text-blue-600 animate-pulse">Processing document...</p>
        : <p className="text-gray-500">Drop a PDF here or click to upload</p>}
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
    </div>
  )
}
