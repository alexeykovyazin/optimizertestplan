SELECT COUNT(*) FROM users as u, postHistory as ph WHERE ph.UserId = u.Id AND u.UpVotes=0 AND ph.PostHistoryTypeId=12
