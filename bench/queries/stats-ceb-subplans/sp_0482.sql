SELECT COUNT(*) FROM badges as b, postLinks as pl, posts as p, users as u WHERE p.Id = pl.RelatedPostId AND u.Id = p.OwnerUserId AND u.Id = b.UserId AND p.ViewCount>=0 AND u.Reputation>=1
