SELECT COUNT(*) FROM users as u, posts as p WHERE p.OwnerUserId = u.Id AND p.PostTypeId=2
