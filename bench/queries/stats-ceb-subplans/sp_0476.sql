SELECT COUNT(*) FROM users as u, postLinks as pl, posts as p WHERE u.Id = p.OwnerUserId AND p.Id = pl.RelatedPostId AND u.Reputation>=1 AND p.ViewCount>=0
