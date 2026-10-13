SELECT COUNT(*) FROM votes as v, comments as c, users as u WHERE c.UserId = u.Id AND v.UserId = u.Id AND v.BountyAmount>=0 AND v.CreationDate>=CAST('2010-05-19 00:00:00' AS TIMESTAMP) AND c.Score=2
