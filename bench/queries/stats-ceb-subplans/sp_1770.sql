SELECT COUNT(*) FROM posts as p, postHistory as ph, users as u WHERE p.OwnerUserId = u.Id AND ph.UserId = u.Id AND p.ViewCount>=0 AND p.ViewCount<=2024 AND ph.PostHistoryTypeId=5
