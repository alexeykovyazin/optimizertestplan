SELECT COUNT(*) FROM users as u, posts as p, postLinks as pl WHERE p.OwnerUserId = u.Id AND p.Id = pl.RelatedPostId AND u.UpVotes>=0 AND u.CreationDate>=CAST('2010-08-21 21:27:38' AS TIMESTAMP)
