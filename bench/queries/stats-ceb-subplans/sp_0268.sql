SELECT COUNT(*) FROM badges as b, users as u WHERE b.UserId = u.Id AND u.Views>=0 AND u.DownVotes>=0 AND u.DownVotes<=0 AND u.UpVotes>=0 AND u.UpVotes<=37
