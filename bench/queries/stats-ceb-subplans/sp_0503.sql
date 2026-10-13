SELECT COUNT(*) FROM postHistory as ph, posts as p, users as u WHERE u.Id = p.OwnerUserId AND u.Id = ph.UserId AND p.CommentCount>=0
