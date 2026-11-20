import duckdb, time, sys
t=time.time()
con=duckdb.connect()
con.sql("set memory_limit='6GB'; set threads=4")
src='data/specmine_zenodo/x/specmine-zenodo/specs.jsonl.gz'
con.sql(f"""copy (select * from read_ndjson('{src}', maximum_object_size=268435456, compression='gzip'))
  to 'data/derived/specs_text.parquet' (format parquet, compression zstd)""")
print('ok', round(time.time()-t), 's')
