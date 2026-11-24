select version();
select name, setting, unit from pg_settings
 where name in ('shared_buffers', 'work_mem', 'hash_mem_multiplier', 'effective_cache_size',
                'max_parallel_workers_per_gather', 'max_parallel_workers', 'max_worker_processes',
                'random_page_cost', 'seq_page_cost', 'jit', 'default_statistics_target', 'enable_memoize')
 order by 1;
select tablename, indexname, indexdef from pg_indexes where schemaname = 'public' order by 1, 2;
select relname, reltuples::bigint as row_estimate, pg_size_pretty(pg_total_relation_size(oid)) as total_size
  from pg_class where relkind = 'r' and relnamespace = 'public'::regnamespace order by 1;
select relname, last_analyze, last_autoanalyze from pg_stat_user_tables order by 1;
