SELECT COUNT(*) FROM badges as b, users as u WHERE u.Id = b.UserId AND u.Reputation>=1
