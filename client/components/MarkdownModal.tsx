"use client"

import ReactMarkdown from "react-markdown"

type MarkdownModalProps = {
  open: boolean
  title: string
  content: string
  loading: boolean
  onClose: () => void
}

export default function MarkdownModal({
  open,
  title,
  content,
  loading,
  onClose,
}: MarkdownModalProps) {
  if (!open) {
    return null
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="modal-header">
          <div className="modal-title">{title}</div>
          <button className="button secondary" onClick={onClose} type="button">
            Закрыть
          </button>
        </div>
        <div className="modal-content">
          {loading ? (
            <p className="muted">Загрузка...</p>
          ) : (
            <div className="markdown">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
