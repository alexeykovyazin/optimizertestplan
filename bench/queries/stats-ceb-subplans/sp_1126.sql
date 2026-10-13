SELECT COUNT(*) FROM votes as v, comments as c, posts as p, postHistory as ph WHERE p.Id = v.PostId AND p.Id = c.PostId AND p.Id = ph.PostId AND c.Score=0 AND p.Score<=67 AND ph.PostHistoryTypeId=34
