SELECT COUNT(*) FROM users as u, postHistory as ph WHERE ph.UserId = u.Id AND u.Reputation>=1 AND u.Reputation<=750 AND ph.PostHistoryTypeId=5
