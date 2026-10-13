SELECT COUNT(*) FROM postLinks as pl, comments as c, posts as p WHERE pl.PostId = p.Id AND c.PostId = p.Id AND c.CreationDate>=CAST('2010-08-02 23:52:10' AS TIMESTAMP)
