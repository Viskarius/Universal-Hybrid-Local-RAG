import Link from "next/link"

export default function HomePage() {
  return (
    <section className="hero">
      <div>
        <h1>Документы превращаются в Markdown за один шаг</h1>
        <p>
          Загрузите файл, мы бережно конвертируем его через Docling и сохраняем
          чистый Markdown в базу. Быстро, прозрачно и готово к дальнейшим
          модулям.
        </p>
      </div>
      <div className="actions">
        <Link className="button" href="/upload">
          Загрузить документ
        </Link>
        <Link className="button secondary" href="/documents">
          Посмотреть базу
        </Link>
      </div>

      <div>
        <h2 className="section-title">Как это работает</h2>
        <div className="grid">
          <div className="card">
            <strong>Асинхронная загрузка</strong>
            <span className="muted">
              Файлы сохраняются чанками и ставятся в очередь на обработку.
            </span>
          </div>
          <div className="card">
            <strong>Конвертация Docling</strong>
            <span className="muted">
              Поддержка PDF, DOCX, PPTX, HTML, Markdown, AsciiDoc и изображений.
            </span>
          </div>
          <div className="card">
            <strong>Markdown в Postgres</strong>
            <span className="muted">
              Результат сохраняется в базе, а временный файл удаляется.
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
