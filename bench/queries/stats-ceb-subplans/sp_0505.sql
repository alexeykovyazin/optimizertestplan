SELECT COUNT(*) FROM postHistory as ph, users as u WHERE u.Id = ph.UserId AND u.DownVotes<=0
