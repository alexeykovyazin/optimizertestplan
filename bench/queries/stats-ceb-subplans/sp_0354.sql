SELECT COUNT(*) FROM users as u, postHistory as ph, badges as b WHERE b.UserId = u.Id AND ph.UserId = u.Id AND u.UpVotes=0 AND ph.PostHistoryTypeId=12
