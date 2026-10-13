SELECT COUNT(*) FROM votes as v, posts as p, postHistory as ph WHERE p.Id = v.PostId AND p.Id = ph.PostId AND v.VoteTypeId=5 AND p.CommentCount>=0 AND ph.PostHistoryTypeId=2
