SELECT COUNT(*) FROM users as u, votes as v, posts as p WHERE p.OwnerUserId = u.Id AND v.UserId = u.Id AND u.Views>=0 AND p.PostTypeId=2 AND p.CreationDate<=CAST('2014-08-26 22:40:26' AS TIMESTAMP)
