SELECT COUNT(*) FROM badges as b, users as u WHERE u.Id = b.UserId AND u.CreationDate>=CAST('2011-02-08 18:11:37' AS TIMESTAMP)
