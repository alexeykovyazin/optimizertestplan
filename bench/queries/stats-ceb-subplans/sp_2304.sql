SELECT COUNT(*) FROM users as u, comments as c, postLinks as pl, votes as v, posts as p WHERE p.Id = c.PostId AND c.UserId = u.Id AND p.Id = pl.RelatedPostId AND p.Id = v.PostId AND pl.LinkTypeId=1
