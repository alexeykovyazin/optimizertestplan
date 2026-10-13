SELECT COUNT(*) FROM postHistory as ph, comments as c, posts as p WHERE p.Id = c.PostId AND p.Id = ph.PostId AND ph.PostHistoryTypeId=34 AND c.Score=0 AND p.Score<=67
