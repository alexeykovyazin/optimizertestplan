SELECT COUNT(*) FROM users as u, postHistory as ph WHERE ph.UserId = u.Id AND u.Reputation>=1 AND u.Views<=80 AND u.UpVotes>=0 AND u.CreationDate>=CAST('2010-08-02 20:31:12' AS TIMESTAMP)
