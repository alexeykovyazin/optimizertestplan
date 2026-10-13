SELECT COUNT(*) FROM posts as p, postHistory as ph WHERE p.Id = ph.PostId AND p.PostTypeId=1 AND p.Score>=-1 AND p.CommentCount>=0 AND p.CommentCount<=11
