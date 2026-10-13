SELECT COUNT(*) FROM votes as v, comments as c, postHistory as ph, users as u WHERE c.UserId = u.Id AND ph.UserId = u.Id AND v.UserId = u.Id AND v.BountyAmount<=50 AND ph.PostHistoryTypeId=3
