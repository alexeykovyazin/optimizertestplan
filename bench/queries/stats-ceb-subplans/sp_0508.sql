SELECT COUNT(*) FROM users as u, tags as t, posts as p WHERE p.Id = t.ExcerptPostId AND u.Id = p.OwnerUserId AND u.DownVotes<=0 AND p.CommentCount>=0
