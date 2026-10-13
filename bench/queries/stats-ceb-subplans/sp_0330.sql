SELECT COUNT(*) FROM users as u, postHistory as ph, votes as v WHERE v.UserId = u.Id AND ph.UserId = u.Id AND u.DownVotes>=0 AND ph.PostHistoryTypeId=3 AND v.BountyAmount<=50
