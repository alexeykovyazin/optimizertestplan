SELECT COUNT(*) FROM users as u, posts as p WHERE u.Id = p.OwnerUserId AND u.Views>=0 AND u.Views<=75 AND p.Score>=-2 AND p.ViewCount>=0 AND p.ViewCount<=18281
