SELECT COUNT(*) FROM postHistory as ph, tags as t, posts as p, users as u WHERE p.Id = t.ExcerptPostId AND u.Id = p.OwnerUserId AND u.Id = ph.UserId AND p.CommentCount>=0
