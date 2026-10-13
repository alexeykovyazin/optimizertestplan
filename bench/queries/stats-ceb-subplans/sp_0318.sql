SELECT COUNT(*) FROM votes as v, postHistory as ph, users as u WHERE v.UserId = u.Id AND ph.UserId = u.Id AND v.BountyAmount<=50 AND ph.PostHistoryTypeId=3
