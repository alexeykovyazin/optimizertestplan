SELECT COUNT(*) FROM users as u, posts as p, votes as v WHERE u.Id = p.OwnerUserId AND p.Id = v.PostId AND p.PostTypeId=1 AND p.Score>=-1 AND p.CommentCount>=0 AND p.CommentCount<=11
