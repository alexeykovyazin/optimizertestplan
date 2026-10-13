SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE p.Id = ph.PostId AND ph.PostHistoryTypeId=2 AND p.CommentCount>=0
