import { NextResponse } from "next/server"

import { getPool } from "@/lib/db"

export async function GET() {
  try {
    const pool = getPool()
    const result = await pool.query(
      "SELECT id, created_at FROM documents ORDER BY created_at DESC"
    )
    return NextResponse.json({ items: result.rows })
  } catch (_error) {
    return NextResponse.json(
      { error: "Failed to load documents" },
      { status: 500 }
    )
  }
}
