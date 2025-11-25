import pg from 'pg';
import { DB_URL } from '$env/static/private';

const Pool = pg.Pool;

export const pool = new Pool({
    connectionString: DB_URL
});

export async function runQuery(query: string) {
    try {
        const res = await pool.query(query);
        return {
            rows: res.rows,
            fields: res.fields,
            rowCount: res.rowCount,
            command: res.command,
            oid: res.oid
        };
    } catch (err) {
        console.error('Database query error:', err);
        throw err;
    }
}