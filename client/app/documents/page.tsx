"use client"

import { useEffect, useMemo, useState } from "react"

import MarkdownModal from "@/components/MarkdownModal"

type DocumentItem = {
  id: string
  created_at: string | null
}

type DocumentDetail = {
  id: string
  content: string
  created_at: string | null
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [active, setActive] = useState<DocumentDetail | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalLoading, setModalLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const formatter = useMemo(
    () =>
      new Intl.DateTimeFormat("ru-RU", {
        dateStyle: "medium",
        timeStyle: "short",
      }),
    []
  )

  useEffect(() => {
    const load = async () => {
      try {
        const response = await fetch("/api/documents")
        if (!response.ok) {
          throw new Error("Не удалось получить список")
        }
        const data = await response.json()
        setDocuments(data.items || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки")
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  const openDocument = async (doc: DocumentItem) => {
    setModalOpen(true)
    setModalLoading(true)
    setActive({ id: doc.id, content: "", created_at: doc.created_at })

    try {
      const response = await fetch(`/api/documents/${doc.id}`)
      if (!response.ok) {
        throw new Error("Не удалось загрузить документ")
      }
      const data = await response.json()
      setActive(data)
    } catch (err) {
      setActive({
        id: doc.id,
        content: "Не удалось загрузить Markdown.",
        created_at: doc.created_at,
      })
    } finally {
      setModalLoading(false)
    }
  }

  const deleteDocument = async (docId: string) => {
    const confirmDelete = window.confirm(
      "Удалить документ без возможности восстановления?"
    )
    if (!confirmDelete) {
      return
    }

    setDeletingId(docId)
    setError(null)

    try {
      const response = await fetch(`/api/documents/${docId}`, {
        method: "DELETE",
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        const message = payload.error || "Не удалось удалить документ"
        throw new Error(message)
      }
      setDocuments((prev) => prev.filter((doc) => doc.id !== docId))
      if (active?.id === docId) {
        setModalOpen(false)
        setActive(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка удаления")
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section>
      <h2 className="section-title">Документы в базе</h2>
      {loading && <p className="muted">Загрузка списка...</p>}
      {error && <div className="status error">{error}</div>}
      {!loading && !error && documents.length === 0 && (
        <p className="muted">Пока нет загруженных документов.</p>
      )}
      <div className="doc-list">
        {documents.map((doc) => (
          <div className="doc-card" key={doc.id}>
            <div className="doc-meta">
              <span className="doc-id">{doc.id}</span>
              <span className="muted">
                {doc.created_at
                  ? formatter.format(new Date(doc.created_at))
                  : "Дата неизвестна"}
              </span>
            </div>
            <div className="doc-actions">
              <button
                className="doc-action"
                type="button"
                onClick={() => openDocument(doc)}
              >
                Открыть
              </button>
              <button
                className="doc-action danger"
                type="button"
                onClick={() => deleteDocument(doc.id)}
                disabled={deletingId === doc.id}
              >
                {deletingId === doc.id ? "Удаление..." : "Удалить"}
              </button>
            </div>
          </div>
        ))}
      </div>

      <MarkdownModal
        open={modalOpen}
        title={active?.id ?? "Документ"}
        content={active?.content ?? ""}
        loading={modalLoading}
        onClose={() => {
          setModalOpen(false)
          setActive(null)
        }}
      />
    </section>
  )
}
