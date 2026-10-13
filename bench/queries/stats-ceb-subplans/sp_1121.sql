SELECT COUNT(*) FROM votes as v, posts as p, postHistory as ph WHERE p.Id = v.PostId AND p.Id = ph.PostId AND p.Score<=67 AND ph.PostHistoryTypeId=34
