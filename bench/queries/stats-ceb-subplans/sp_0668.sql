SELECT COUNT(*) FROM badges as b, posts as p, postLinks as pl, votes as v, users as u WHERE u.Id = p.OwnerUserId AND p.Id = pl.RelatedPostId AND p.Id = v.PostId AND u.Id = b.UserId
