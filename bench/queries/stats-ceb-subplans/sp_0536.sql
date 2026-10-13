SELECT COUNT(*) FROM badges as b, tags as t, posts as p, votes as v, users as u WHERE p.Id = t.ExcerptPostId AND u.Id = p.OwnerUserId AND u.Id = b.UserId AND u.Id = v.UserId
