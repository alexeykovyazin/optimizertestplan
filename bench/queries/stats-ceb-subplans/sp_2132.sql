SELECT COUNT(*) FROM votes as v, users as u WHERE u.Id = v.UserId AND u.Reputation>=1
