set list on;
select rdb$get_context('SYSTEM', 'ENGINE_VERSION') as engine_version, mon$page_size, mon$page_buffers,
       mon$pages from mon$database;
set list off;
select trim(i.rdb$relation_name) as tab, trim(i.rdb$index_name) as idx, i.rdb$unique_flag as uniq,
       (select list(trim(s.rdb$field_name)) from rdb$index_segments s
         where s.rdb$index_name = i.rdb$index_name) as fields
  from rdb$indices i
 where coalesce(i.rdb$system_flag, 0) = 0
 order by 1, 2;
select trim(rdb$relation_name) as stat_table from rdb$relations where rdb$relation_name starting with 'STAT$';
