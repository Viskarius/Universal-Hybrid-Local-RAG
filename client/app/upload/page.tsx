"use client"

import type { FormEvent } from "react"
import { useState } from "react"

const acceptedFormats = [
  "pdf",
  "docx",
  "pptx",
  "md",
  "markdown",
  "html",
  "htm",
  "adoc",
  "asciidoc",
  "png",
  "jpg",
  "jpeg",
  "tiff",
  "tif",
  "bmp",
  "webp",
]

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  const apiKey = process.env.NEXT_PUBLIC_API_KEY

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setStatus(null)
    setError(null)

    if (!apiUrl || !apiKey) {
      setError("Отсутствуют настройки API. Проверьте .env")
      return
    }

    if (!file) {
      setError("Выберите файл для загрузки")
      return
    }

    const formData = new FormData()
    formData.append("file", file)

    try {
      setLoading(true)
      const response = await fetch(`${apiUrl}/upload`, {
        method: "POST",
        headers: {
          "X-API-Key": apiKey,
        },
        body: formData,
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        const message = payload.detail || "Ошибка загрузки"
        throw new Error(message)
      }

      const data = await response.json()
      setStatus(`Файл принят. ID: ${data.id}`)
      setFile(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки")
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="upload-panel">
      <div>
        <h2>Загрузка документов</h2>
        <p className="muted">
          Документ будет обработан и сохранен в Markdown. Поддерживаемые форматы:
          {" "}
          {acceptedFormats.join(", ")}.
        </p>
      </div>
      <form className="upload-form" onSubmit={onSubmit}>
        <input
          className="file-input"
          type="file"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
          accept={acceptedFormats.map((ext) => `.${ext}`).join(",")}
        />
        <button className="button" type="submit" disabled={loading}>
          {loading ? "Загрузка..." : "Отправить файл"}
        </button>
      </form>
      {status && <div className="status">{status}</div>}
      {error && <div className="status error">{error}</div>}
    </section>
  )
}
