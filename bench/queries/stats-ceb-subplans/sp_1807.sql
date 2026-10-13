SELECT COUNT(*) FROM badges as b, posts as p, users as u WHERE p.OwnerUserId = u.Id AND b.UserId = u.Id AND p.PostTypeId=2
