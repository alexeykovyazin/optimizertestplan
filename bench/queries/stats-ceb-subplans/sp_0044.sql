SELECT COUNT(*) FROM tags as t, posts as p WHERE p.Id = t.ExcerptPostId AND p.CreationDate>=CAST('2010-07-20 02:01:05' AS TIMESTAMP)
