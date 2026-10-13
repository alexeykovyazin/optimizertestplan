SELECT COUNT(*) FROM posts as p, comments as c WHERE c.PostId = p.Id AND p.Score>=-3 AND c.CreationDate>=CAST('2010-08-02 23:52:10' AS TIMESTAMP)
