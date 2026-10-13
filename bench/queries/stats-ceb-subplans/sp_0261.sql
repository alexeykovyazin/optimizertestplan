SELECT COUNT(*) FROM badges as b, posts as p, users as u WHERE p.OwnerUserId = u.Id AND b.UserId = u.Id AND p.Score>=-7 AND u.Reputation>=1 AND u.UpVotes>=0 AND u.UpVotes<=117
