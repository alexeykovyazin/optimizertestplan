SELECT COUNT(*) FROM badges as b, posts as p, users as u WHERE u.Id = p.OwnerUserId AND u.Id = b.UserId AND b."Date"<=CAST('2014-08-22 02:21:55' AS TIMESTAMP) AND p.CommentCount>=0
