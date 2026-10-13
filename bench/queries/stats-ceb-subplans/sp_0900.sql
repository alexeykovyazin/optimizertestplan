SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE p.Id = ph.PostId AND ph.PostHistoryTypeId=1 AND p.PostTypeId=1 AND p.Score=4 AND p.ViewCount<=4937
