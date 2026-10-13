SELECT COUNT(*) FROM posts as p WHERE p.Score>=0 AND p.Score<=16 AND p.ViewCount>=0 AND p.CreationDate<=CAST('2014-09-09 12:00:50' AS TIMESTAMP)
