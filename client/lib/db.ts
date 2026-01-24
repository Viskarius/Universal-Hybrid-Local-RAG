import { Pool } from "pg"

let pool: Pool | null = null

export function getPool(): Pool {
  if (!pool) {
    const connectionString = process.env.POSTGRES_URL
    if (!connectionString) {
      throw new Error("POSTGRES_URL is not set")
    }
    pool = new Pool({ connectionString })
  }
  return pool
}
