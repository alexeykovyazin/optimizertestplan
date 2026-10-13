SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE p.Id = ph.PostId AND p.Score<=32 AND p.ViewCount<=4146
