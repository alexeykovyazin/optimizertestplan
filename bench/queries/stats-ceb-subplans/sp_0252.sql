SELECT COUNT(*) FROM posts as p, postHistory as ph, users as u WHERE p.OwnerUserId = u.Id AND ph.UserId = u.Id AND p.Score>=-7 AND ph.PostHistoryTypeId=3
