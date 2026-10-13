SELECT COUNT(*) FROM users as u, postHistory as ph WHERE ph.UserId = u.Id AND u.Reputation>=1 AND u.UpVotes>=0 AND u.UpVotes<=117 AND ph.PostHistoryTypeId=3
