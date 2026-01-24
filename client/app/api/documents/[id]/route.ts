import { NextResponse } from "next/server"

import { getPool } from "@/lib/db"

const uuidRegex =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export async function GET(
  _request: Request,
  { params }: { params: { id: string } }
) {
  const { id } = params
  if (!uuidRegex.test(id)) {
    return NextResponse.json({ error: "Invalid id" }, { status: 400 })
  }

  try {
    const pool = getPool()
    const result = await pool.query(
      "SELECT id, content, created_at FROM documents WHERE id = $1",
      [id]
    )
    if (result.rows.length === 0) {
      return NextResponse.json({ error: "Not found" }, { status: 404 })
    }
    return NextResponse.json(result.rows[0])
  } catch (_error) {
    return NextResponse.json({ error: "Failed to load document" }, { status: 500 })
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: { id: string } }
) {
  const { id } = params
  if (!uuidRegex.test(id)) {
    return NextResponse.json({ error: "Invalid id" }, { status: 400 })
  }

  try {
    const pool = getPool()
    const result = await pool.query(
      "DELETE FROM documents WHERE id = $1 RETURNING id",
      [id]
    )
    if (result.rows.length === 0) {
      return NextResponse.json({ error: "Not found" }, { status: 404 })
    }
    return NextResponse.json({ id: result.rows[0].id })
  } catch (_error) {
    return NextResponse.json({ error: "Failed to delete document" }, { status: 500 })
  }
}
