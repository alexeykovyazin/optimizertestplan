SELECT COUNT(*) FROM badges as b, tags as t, posts as p, users as u WHERE p.Id = t.ExcerptPostId AND u.Id = p.OwnerUserId AND u.Id = b.UserId AND b."Date"<=CAST('2014-09-12 12:56:22' AS TIMESTAMP)
