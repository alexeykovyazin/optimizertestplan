SELECT COUNT(*) FROM badges as b, votes as v, users as u WHERE u.Id = b.UserId AND u.Id = v.UserId AND u.Views>=0
