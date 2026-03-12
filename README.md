Dashboard for integration and visualization of differential cell-cell communicaiton inference and TF analyses results from scRNAseq data.

## Getting Started

Start the backend services

```
docker compose up -d
```

Set up the database:

```
cat ./data/ingest_data/you_sql_db.sql  | docker compose exec -T db psql -U postgres -d diffcellsig
```
Push the schema to `puppygraph`:
```
curl -XPOST -H "content-type: application/json" --data-binary @./backend/schema.json --user "puppygraph:puppygraph123" localhost:8081/schema
```