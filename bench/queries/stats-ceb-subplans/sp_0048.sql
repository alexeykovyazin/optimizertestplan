SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE ph.PostId = p.Id AND ph.CreationDate>=CAST('2010-07-20 00:30:00' AS TIMESTAMP) AND p.CreationDate>=CAST('2010-07-19 20:08:37' AS TIMESTAMP)
