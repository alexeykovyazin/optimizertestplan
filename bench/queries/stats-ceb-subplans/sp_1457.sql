SELECT COUNT(*) FROM posts as p, votes as v, users as u WHERE p.OwnerUserId = u.Id AND v.UserId = u.Id AND p.CommentCount>=0
