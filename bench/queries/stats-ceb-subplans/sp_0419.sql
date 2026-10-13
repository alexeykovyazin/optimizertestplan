SELECT COUNT(*) FROM postHistory as ph, posts as p, users as u WHERE u.Id = p.OwnerUserId AND u.Id = ph.UserId AND ph.PostHistoryTypeId=2 AND p.Score>=-2 AND p.ViewCount>=0 AND p.ViewCount<=18281
