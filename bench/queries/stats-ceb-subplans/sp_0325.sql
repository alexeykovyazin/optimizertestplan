SELECT COUNT(*) FROM users as u, comments as c, postHistory as ph WHERE c.UserId = u.Id AND ph.UserId = u.Id AND u.DownVotes>=0 AND ph.PostHistoryTypeId=3
